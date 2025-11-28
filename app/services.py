import csv
import io
from typing import List, Dict, Tuple
from .models import ADUserCSV, GroupMappingCSV, SyncResult, User
import uuid
from .repositories import UserRepository, AuthzRepository

class CSVService:
    def parse_ad_users(self, content: bytes) -> List[ADUserCSV]:
        decoded = content.decode('utf-8')
        reader = csv.DictReader(io.StringIO(decoded))
        users = []
        for row in reader:
            # Handle potential whitespace or case issues in headers if needed
            # Assuming headers: Nombre, Correo, Grupo
            users.append(ADUserCSV(
                nombre=row.get('Nombre', '').strip(),
                correo=row.get('Correo', '').strip(),
                grupo=row.get('Grupo', '').strip()
            ))
        return users

    def parse_group_mapping(self, content: bytes) -> List[GroupMappingCSV]:
        decoded = content.decode('utf-8')
        reader = csv.DictReader(io.StringIO(decoded))
        mappings = []
        for row in reader:
            # Assuming headers: grupo, nrn, roles
            mappings.append(GroupMappingCSV(
                grupo=row.get('grupo', '').strip(),
                nrn=row.get('nrn', '').strip(),
                roles=row.get('roles', '').strip()
            ))
        return mappings

class SyncService:
    def __init__(self, user_repo: UserRepository, authz_repo: AuthzRepository):
        self.user_repo = user_repo
        self.authz_repo = authz_repo
        self.csv_service = CSVService()

    def execute_sync(
        self,
        ad_users_file: bytes,
        mapping_file: bytes,
        dry_run: bool = False,
        force: bool = False
    ) -> SyncResult:
        logs = []
        mode = "DRY RUN" if dry_run else "FORCE" if force else "NORMAL"
        logs.append(f"Starting synchronization process in {mode} mode...")

        if dry_run:
            logs.append("DRY RUN MODE: No actual changes will be made to users or roles.")

        # 1. Parse CSVs
        ad_users = self.csv_service.parse_ad_users(ad_users_file)
        mappings = self.csv_service.parse_group_mapping(mapping_file)

        logs.append(f"Parsed {len(ad_users)} AD users and {len(mappings)} group mappings.")

        # Create a lookup for mappings by group
        # Assuming one group maps to one set of roles for simplicity, or merging?
        # Requirement says: "mapeo entre grupos de AD y namespace"
        # Let's assume (Group) -> (Namespace, Roles)
        mapping_dict = {m.grupo: m for m in mappings}

        # 2. List all users from repository (both active and inactive)
        current_users = self.user_repo.list_all(status=None)  # Fetch all users regardless of status
        current_emails = {u.email.lower(): u for u in current_users}

        # Also build a map to track user status
        all_np_users = self.user_repo.client.list_all_users(status=None)
        user_status_map = {np_user.email.lower(): np_user.status for np_user in all_np_users}

        ad_emails = {u.correo.lower() for u in ad_users}

        users_processed = 0
        users_deleted = 0
        users_updated = 0
        users_created = 0

        # 3. Deactivate users not in AD CSV (only if they're currently active)
        for email, user in current_emails.items():
            if email not in ad_emails:
                current_status = user_status_map.get(email, "active")
                if current_status == "active":
                    if dry_run:
                        logs.append(f"[DRY RUN] Would mark user {user.email} as inactive (not in AD file).")
                        users_deleted += 1
                    else:
                        try:
                            self.user_repo.delete(user.id)
                            logs.append(f"User {user.email} not found in AD file. Marked as inactive.")
                            users_deleted += 1
                        except Exception as e:
                            logs.append(f"Error deactivating user {user.email}: {str(e)}")
                else:
                    logs.append(f"User {user.email} already inactive. Skipping.")

        # 4. Group AD users by email to handle multiple NRNs per user
        # Structure: { email: { nrn: [roles], nrn2: [roles2], ... } }
        user_nrn_roles: Dict[str, Dict[str, List[str]]] = {}
        user_names: Dict[str, str] = {}  # Track username for each email

        for ad_user in ad_users:
            email_lower = ad_user.correo.lower()

            # Store username (use first occurrence)
            if email_lower not in user_names:
                user_names[email_lower] = ad_user.nombre

            # Get mapping for this group
            mapping = mapping_dict.get(ad_user.grupo)
            if not mapping:
                logs.append(f"No mapping found for group {ad_user.grupo} for user {ad_user.correo}. Skipping.")
                continue

            # Parse comma-separated roles
            expected_roles = [r.strip() for r in mapping.roles.split(',') if r.strip()]

            # Parse comma-separated NRNs (e.g., "nrn:app1,nrn:app2")
            nrns = [n.strip() for n in mapping.nrn.split(',') if n.strip()]

            # Initialize user entry if needed
            if email_lower not in user_nrn_roles:
                user_nrn_roles[email_lower] = {}

            # Apply the same roles to all NRNs in this mapping
            for nrn in nrns:
                # Store roles for this NRN (handle duplicate rows by merging roles)
                if nrn in user_nrn_roles[email_lower]:
                    # Merge roles if same user+nrn appears multiple times
                    user_nrn_roles[email_lower][nrn].extend(expected_roles)
                    user_nrn_roles[email_lower][nrn] = list(set(user_nrn_roles[email_lower][nrn]))
                else:
                    user_nrn_roles[email_lower][nrn] = expected_roles

        # 5. Process each unique user
        for email_lower, nrn_roles_map in user_nrn_roles.items():
            users_processed += 1
            user = self.user_repo.get_by_email(email_lower)
            user_was_updated = False  # Track if this specific user had any updates

            if not user:
                # User not found - create new user
                if dry_run:
                    logs.append(f"[DRY RUN] Would create new user {email_lower}.")
                    users_created += 1
                    continue
                else:
                    try:
                        new_user = User(
                            id="temp",
                            username=user_names[email_lower],
                            email=email_lower,
                            roles=[]
                        )
                        created_user = self.user_repo.create(new_user)
                        user = created_user
                        logs.append(f"User {email_lower} not found in repo. Created with ID {user.id}.")
                        users_created += 1
                    except Exception as e:
                        logs.append(f"Error creating user {email_lower}: {str(e)}")
                        continue
            else:
                # User exists - check if inactive and reactivate if needed
                current_status = user_status_map.get(email_lower, "active")
                if current_status == "inactive":
                    if dry_run:
                        logs.append(f"[DRY RUN] Would reactivate inactive user {email_lower}.")
                    else:
                        try:
                            self.user_repo.reactivate(user.id)
                            logs.append(f"User {email_lower} was inactive. Reactivated.")
                            users_created += 1  # Count reactivation as creation
                        except Exception as e:
                            logs.append(f"Error reactivating user {email_lower}: {str(e)}")
                            continue

            # Get all current grants for this user
            try:
                all_current_grants = self.authz_repo.client.get_user_grants(int(user.id))

                # Build set of all NRNs from current grants
                current_nrns = set()
                if all_current_grants:
                    for grant_response in all_current_grants:
                        for grant in grant_response.grants:
                            current_nrns.add(grant.nrn)

                # Expected NRNs from CSV
                expected_nrns = set(nrn_roles_map.keys())

                # Delete grants for NRNs not in CSV
                nrns_to_delete = current_nrns - expected_nrns
                for nrn in nrns_to_delete:
                    if dry_run:
                        logs.append(f"[DRY RUN] Would delete all grants for user {email_lower} in NRN '{nrn}' (not in CSV).")
                    else:
                        # Delete all grants for this NRN
                        self.authz_repo.update_roles(user.id, nrn, [])
                        logs.append(f"Deleted all grants for user {email_lower} in NRN '{nrn}' (not in CSV).")
                    user_was_updated = True  # Mark user as updated if we deleted any grants

                # Update roles for each NRN in the CSV
                for nrn, expected_roles in nrn_roles_map.items():
                    current_roles = self.authz_repo.get_roles(user.id, nrn)

                    if set(current_roles) != set(expected_roles):
                        if dry_run:
                            logs.append(f"[DRY RUN] Would update user {email_lower} roles in NRN '{nrn}' from {current_roles} to {expected_roles}.")
                        else:
                            self.authz_repo.update_roles(user.id, nrn, expected_roles)
                            logs.append(f"User {email_lower} roles in NRN '{nrn}' updated from {current_roles} to {expected_roles}.")
                        user_was_updated = True  # Mark user as updated
                    else:
                        logs.append(f"User {email_lower} roles in NRN '{nrn}' match. No update needed.")

                # Increment users_updated only once per user
                if user_was_updated:
                    users_updated += 1

            except Exception as e:
                logs.append(f"Error processing roles for user {email_lower}: {str(e)}")

        logs.append("Synchronization completed.")

        return SyncResult(
            status="success",
            users_processed=users_processed,
            users_deleted=users_deleted,
            users_updated=users_updated,
            users_created=users_created,
            logs=logs
        )
