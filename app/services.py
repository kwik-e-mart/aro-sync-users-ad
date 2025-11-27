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

        # 2. List all users from repository
        current_users = self.user_repo.list_all()
        current_emails = {u.email.lower(): u for u in current_users}

        ad_emails = {u.correo.lower() for u in ad_users}

        users_processed = 0
        users_deleted = 0
        users_updated = 0
        users_created = 0

        # 3. Compare and Delete missing users (users not in AD CSV)
        for email, user in current_emails.items():
            if email not in ad_emails:
                if dry_run:
                    logs.append(f"[DRY RUN] Would mark user {user.email} as inactive (not in AD file).")
                    users_deleted += 1
                else:
                    try:
                        self.user_repo.delete(user.id)
                        logs.append(f"User {user.email} not found in AD file. Marked as inactive.")
                        users_deleted += 1
                    except Exception as e:
                        logs.append(f"Error deleting user {user.email}: {str(e)}")

        # 4. Match and Validate/Update roles (using email as primary key)
        for ad_user in ad_users:
            users_processed += 1
            user = self.user_repo.get_by_email(ad_user.correo)

            if not user:
                # Create new user
                if dry_run:
                    logs.append(f"[DRY RUN] Would create new user {ad_user.correo}.")
                    users_created += 1
                    continue
                else:
                    try:
                        new_user = User(
                            id="temp",
                            username=ad_user.nombre,
                            email=ad_user.correo,
                            roles=[]
                        )
                        created_user = self.user_repo.create(new_user)
                        user = created_user
                        logs.append(f"User {ad_user.correo} not found in repo. Created with ID {user.id}.")
                        users_created += 1
                    except Exception as e:
                        logs.append(f"Error creating user {ad_user.correo}: {str(e)}")
                        continue

            # Determine expected roles based on group
            mapping = mapping_dict.get(ad_user.grupo)
            if not mapping:
                logs.append(f"No mapping found for group {ad_user.grupo} for user {ad_user.correo}. Skipping role update.")
                continue

            expected_roles = [r.strip() for r in mapping.roles.split(',')]
            nrn = mapping.nrn

            # Check current roles for this NRN
            try:
                current_roles = self.authz_repo.get_roles(user.id, nrn)

                # Simple comparison - order independent
                if set(current_roles) != set(expected_roles):
                    if dry_run:
                        logs.append(f"[DRY RUN] Would update user {ad_user.correo} roles in NRN '{nrn}' from {current_roles} to {expected_roles}.")
                        users_updated += 1
                    else:
                        self.authz_repo.update_roles(user.id, nrn, expected_roles)
                        logs.append(f"User {ad_user.correo} roles in NRN '{nrn}' updated from {current_roles} to {expected_roles}.")
                        users_updated += 1
                else:
                    logs.append(f"User {ad_user.correo} roles in NRN '{nrn}' match. No update needed.")
            except Exception as e:
                logs.append(f"Error updating roles for user {ad_user.correo} in NRN '{nrn}': {str(e)}")

        logs.append("Synchronization completed.")

        return SyncResult(
            status="success",
            users_processed=users_processed,
            users_deleted=users_deleted,
            users_updated=users_updated,
            users_created=users_created,
            logs=logs
        )
