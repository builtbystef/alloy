export interface paths {
    "/health/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Read Health
         * @description Liveness: the process is up.
         */
        get: operations["health-read_health"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health/db": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Read Health Db
         * @description Readiness: the database answers.
         */
        get: operations["health-read_health_db"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/auth/signup": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Signup
         * @description Create an account, a first workspace owned by it, and log in.
         */
        post: operations["auth-signup"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/auth/login": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Login */
        post: operations["auth-login"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/auth/logout": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Logout
         * @description Revoke this session.
         */
        post: operations["auth-logout"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/auth/logout-all": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Logout All
         * @description Revoke every session of the user: log out everywhere.
         */
        post: operations["auth-logout_all"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/auth/password": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Change Password
         * @description Set a new password. Every other session is revoked; this one stays logged in.
         */
        post: operations["auth-change_password"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/auth/me": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Me */
        get: operations["auth-read_me"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workspaces/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Workspaces
         * @description Every workspace the caller belongs to, oldest first.
         */
        get: operations["workspaces-list_workspaces"];
        put?: never;
        /**
         * Create Workspace Route
         * @description The caller becomes its owner.
         */
        post: operations["workspaces-create_workspace_route"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workspaces/{workspace_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Workspace */
        get: operations["workspaces-read_workspace"];
        put?: never;
        post?: never;
        /**
         * Delete Workspace
         * @description Owners only. Members, invitations, and every CRM record go with it.
         */
        delete: operations["workspaces-delete_workspace"];
        options?: never;
        head?: never;
        /** Update Workspace */
        patch: operations["workspaces-update_workspace"];
        trace?: never;
    };
    "/workspaces/{workspace_id}/leave": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Leave Workspace
         * @description Give up the caller's seat. The last owner cannot leave; delete the workspace or
         *     make someone else an owner first.
         */
        post: operations["workspaces-leave_workspace"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workspaces/{workspace_id}/members": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Members
         * @description Longest-standing first.
         */
        get: operations["workspaces-list_members"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workspaces/{workspace_id}/members/{member_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /**
         * Remove Member
         * @description Remove someone else's seat; use `leave` for your own.
         */
        delete: operations["workspaces-remove_member"];
        options?: never;
        head?: never;
        /**
         * Update Member
         * @description Change a role. The caller must outrank both the current and the new role (owners
         *     outrank everyone), and the last owner cannot be demoted.
         */
        patch: operations["workspaces-update_member"];
        trace?: never;
    };
    "/workspaces/{workspace_id}/invites": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Invites
         * @description Pending only: accepted, revoked, and expired invitations are not listed.
         */
        get: operations["workspaces-list_invites"];
        put?: never;
        /**
         * Create Invite
         * @description Email a link that grants `role`. One pending invitation per address; 409 if the
         *     address is already a member or already invited.
         */
        post: operations["workspaces-create_invite"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workspaces/{workspace_id}/invites/{invite_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /**
         * Revoke Invite
         * @description The link stops working. Only pending invitations can be revoked.
         */
        delete: operations["workspaces-revoke_invite"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/invites/{token}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Read Invite
         * @description No login needed: the page shows who invited you where before you sign up.
         */
        get: operations["invites-read_invite"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/invites/{token}/accept": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Accept Invite
         * @description Take the seat. The logged-in account's email must be the invited one.
         */
        post: operations["invites-accept_invite"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workspaces/{workspace_id}/companies/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Companies
         * @description Sorted by name.
         */
        get: operations["companies-list_companies"];
        put?: never;
        /** Create Company */
        post: operations["companies-create_company"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workspaces/{workspace_id}/companies/{company_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Company */
        get: operations["companies-read_company"];
        put?: never;
        post?: never;
        /**
         * Delete Company
         * @description Contacts and tasks at the company are kept, with the link cleared.
         */
        delete: operations["companies-delete_company"];
        options?: never;
        head?: never;
        /** Update Company */
        patch: operations["companies-update_company"];
        trace?: never;
    };
    "/workspaces/{workspace_id}/companies/{company_id}/contacts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Company Contacts */
        get: operations["companies-list_company_contacts"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workspaces/{workspace_id}/contacts/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Contacts
         * @description Sorted by name.
         */
        get: operations["contacts-list_contacts"];
        put?: never;
        /** Create Contact */
        post: operations["contacts-create_contact"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workspaces/{workspace_id}/contacts/{contact_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Contact */
        get: operations["contacts-read_contact"];
        put?: never;
        post?: never;
        /**
         * Delete Contact
         * @description The contact's activities go with it; tasks are kept, with the link cleared.
         */
        delete: operations["contacts-delete_contact"];
        options?: never;
        head?: never;
        /** Update Contact */
        patch: operations["contacts-update_contact"];
        trace?: never;
    };
    "/workspaces/{workspace_id}/contacts/{contact_id}/activities": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Activities
         * @description Newest first.
         */
        get: operations["contacts-list_activities"];
        put?: never;
        /**
         * Create Activity
         * @description A call, email, meeting, or follow-up also marks the contact as contacted now.
         */
        post: operations["contacts-create_activity"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workspaces/{workspace_id}/tasks/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Tasks
         * @description Soonest due first, undated last.
         */
        get: operations["tasks-list_tasks"];
        put?: never;
        /** Create Task */
        post: operations["tasks-create_task"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workspaces/{workspace_id}/tasks/{task_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Task */
        get: operations["tasks-read_task"];
        put?: never;
        post?: never;
        /** Delete Task */
        delete: operations["tasks-delete_task"];
        options?: never;
        head?: never;
        /**
         * Update Task
         * @description Marking a task done logs a `task_completed` activity on its contact.
         */
        patch: operations["tasks-update_task"];
        trace?: never;
    };
    "/workspaces/{workspace_id}/dashboard/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Read Dashboard
         * @description Counts of open tasks due today and overdue, plus who was and was not contacted lately.
         */
        get: operations["dashboard-read_dashboard"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Root */
        get: operations["read_root"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** ActivityCreate */
        ActivityCreate: {
            type: components["schemas"]["ActivityType"];
            /** Notes */
            notes?: string | null;
        };
        /** ActivityRead */
        ActivityRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Contact Id
             * Format: uuid
             */
            contact_id: string;
            type: components["schemas"]["ActivityType"];
            /** Notes */
            notes: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /**
         * ActivityType
         * @enum {string}
         */
        ActivityType: "note" | "call" | "email" | "meeting" | "follow_up" | "task_completed";
        /** CompanyCreate */
        CompanyCreate: {
            /** Name */
            name: string;
            /** Website */
            website?: string | null;
            /** Industry */
            industry?: string | null;
            /** Notes */
            notes?: string | null;
        };
        /** CompanyRead */
        CompanyRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Website */
            website: string | null;
            /** Industry */
            industry: string | null;
            /** Notes */
            notes: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /**
         * CompanyRef
         * @description Enough to link to a company from a contact or task.
         */
        CompanyRef: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
        };
        /** CompanyUpdate */
        CompanyUpdate: {
            /** Name */
            name?: string | null;
            /** Website */
            website?: string | null;
            /** Industry */
            industry?: string | null;
            /** Notes */
            notes?: string | null;
        };
        /** ContactCreate */
        ContactCreate: {
            /** Name */
            name: string;
            /** Email */
            email?: string | null;
            /** Phone */
            phone?: string | null;
            /** Job Title */
            job_title?: string | null;
            /** Company Id */
            company_id?: string | null;
            /** @default lead */
            status: components["schemas"]["ContactStatus"];
            /** Last Contacted At */
            last_contacted_at?: string | null;
        };
        /** ContactRead */
        ContactRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Email */
            email: string | null;
            /** Phone */
            phone: string | null;
            /** Job Title */
            job_title: string | null;
            status: components["schemas"]["ContactStatus"];
            /** Last Contacted At */
            last_contacted_at: string | null;
            company: components["schemas"]["CompanyRef"] | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** ContactRef */
        ContactRef: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
        };
        /**
         * ContactStatus
         * @enum {string}
         */
        ContactStatus: "lead" | "active" | "inactive";
        /** ContactUpdate */
        ContactUpdate: {
            /** Name */
            name?: string | null;
            /** Email */
            email?: string | null;
            /** Phone */
            phone?: string | null;
            /** Job Title */
            job_title?: string | null;
            /** Company Id */
            company_id?: string | null;
            status?: components["schemas"]["ContactStatus"] | null;
            /** Last Contacted At */
            last_contacted_at?: string | null;
        };
        /** Credentials */
        Credentials: {
            /**
             * Email
             * Format: email
             */
            email: string;
            /** Password */
            password: string;
        };
        /** Dashboard */
        Dashboard: {
            /** Total Contacts */
            total_contacts: number;
            /** Tasks Due Today */
            tasks_due_today: number;
            /** Overdue Tasks */
            overdue_tasks: number;
            /** Recently Contacted */
            recently_contacted: components["schemas"]["ContactRead"][];
            /** Not Recently Contacted */
            not_recently_contacted: components["schemas"]["ContactRead"][];
        };
        /**
         * DueFilter
         * @enum {string}
         */
        DueFilter: "overdue" | "today" | "upcoming";
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /** Health */
        Health: {
            /** Status */
            status: string;
        };
        /** InviteCreate */
        InviteCreate: {
            /**
             * Email
             * Format: email
             */
            email: string;
            /** @default member */
            role: components["schemas"]["WorkspaceRole"];
        };
        /**
         * InvitePreview
         * @description What the invitation page shows before the invitee logs in or signs up.
         */
        InvitePreview: {
            /** Workspace Name */
            workspace_name: string;
            /** Email */
            email: string;
            role: components["schemas"]["WorkspaceRole"];
            /** Invited By */
            invited_by: string | null;
            /**
             * Expires At
             * Format: date-time
             */
            expires_at: string;
        };
        /** InviteRead */
        InviteRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Email */
            email: string;
            role: components["schemas"]["WorkspaceRole"];
            /** Invited By */
            invited_by: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Expires At
             * Format: date-time
             */
            expires_at: string;
        };
        /** MemberRead */
        MemberRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * User Id
             * Format: uuid
             */
            user_id: string;
            /** Email */
            email: string;
            role: components["schemas"]["WorkspaceRole"];
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /** MemberUpdate */
        MemberUpdate: {
            role: components["schemas"]["WorkspaceRole"];
        };
        /** PasswordChange */
        PasswordChange: {
            /** Current Password */
            current_password: string;
            /** New Password */
            new_password: string;
        };
        /**
         * Permission
         * @enum {string}
         */
        Permission: "crm:read" | "crm:write" | "members:read" | "members:manage" | "workspace:manage" | "workspace:delete";
        /** TaskCreate */
        TaskCreate: {
            /** Title */
            title: string;
            /** Due At */
            due_at?: string | null;
            /** @default open */
            status: components["schemas"]["TaskStatus"];
            /** Contact Id */
            contact_id?: string | null;
            /** Company Id */
            company_id?: string | null;
            /** Notes */
            notes?: string | null;
        };
        /** TaskRead */
        TaskRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Title */
            title: string;
            /** Due At */
            due_at: string | null;
            status: components["schemas"]["TaskStatus"];
            /** Notes */
            notes: string | null;
            contact: components["schemas"]["ContactRef"] | null;
            company: components["schemas"]["CompanyRef"] | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /**
         * TaskStatus
         * @enum {string}
         */
        TaskStatus: "open" | "done";
        /** TaskUpdate */
        TaskUpdate: {
            /** Title */
            title?: string | null;
            /** Due At */
            due_at?: string | null;
            status?: components["schemas"]["TaskStatus"] | null;
            /** Contact Id */
            contact_id?: string | null;
            /** Company Id */
            company_id?: string | null;
            /** Notes */
            notes?: string | null;
        };
        /** UserRead */
        UserRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Email */
            email: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /** ValidationError */
        ValidationError: {
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
            /** Input */
            input?: unknown;
            /** Context */
            ctx?: Record<string, never>;
        };
        /** WorkspaceCreate */
        WorkspaceCreate: {
            /** Name */
            name: string;
        };
        /**
         * WorkspaceRead
         * @description A workspace as seen by one member: their role and what it allows come along.
         */
        WorkspaceRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
            role: components["schemas"]["WorkspaceRole"];
            /** Permissions */
            permissions: components["schemas"]["Permission"][];
        };
        /**
         * WorkspaceRole
         * @description Ordered from most to least powerful; see permissions.py for what each may do.
         * @enum {string}
         */
        WorkspaceRole: "owner" | "admin" | "member" | "viewer";
        /** WorkspaceUpdate */
        WorkspaceUpdate: {
            /** Name */
            name: string;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type ActivityCreate = components['schemas']['ActivityCreate'];
export type ActivityRead = components['schemas']['ActivityRead'];
export type ActivityType = components['schemas']['ActivityType'];
export type CompanyCreate = components['schemas']['CompanyCreate'];
export type CompanyRead = components['schemas']['CompanyRead'];
export type CompanyRef = components['schemas']['CompanyRef'];
export type CompanyUpdate = components['schemas']['CompanyUpdate'];
export type ContactCreate = components['schemas']['ContactCreate'];
export type ContactRead = components['schemas']['ContactRead'];
export type ContactRef = components['schemas']['ContactRef'];
export type ContactStatus = components['schemas']['ContactStatus'];
export type ContactUpdate = components['schemas']['ContactUpdate'];
export type Credentials = components['schemas']['Credentials'];
export type Dashboard = components['schemas']['Dashboard'];
export type DueFilter = components['schemas']['DueFilter'];
export type HttpValidationError = components['schemas']['HTTPValidationError'];
export type Health = components['schemas']['Health'];
export type InviteCreate = components['schemas']['InviteCreate'];
export type InvitePreview = components['schemas']['InvitePreview'];
export type InviteRead = components['schemas']['InviteRead'];
export type MemberRead = components['schemas']['MemberRead'];
export type MemberUpdate = components['schemas']['MemberUpdate'];
export type PasswordChange = components['schemas']['PasswordChange'];
export type Permission = components['schemas']['Permission'];
export type TaskCreate = components['schemas']['TaskCreate'];
export type TaskRead = components['schemas']['TaskRead'];
export type TaskStatus = components['schemas']['TaskStatus'];
export type TaskUpdate = components['schemas']['TaskUpdate'];
export type UserRead = components['schemas']['UserRead'];
export type ValidationError = components['schemas']['ValidationError'];
export type WorkspaceCreate = components['schemas']['WorkspaceCreate'];
export type WorkspaceRead = components['schemas']['WorkspaceRead'];
export type WorkspaceRole = components['schemas']['WorkspaceRole'];
export type WorkspaceUpdate = components['schemas']['WorkspaceUpdate'];
export type $defs = Record<string, never>;
export interface operations {
    "health-read_health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Health"];
                };
            };
        };
    };
    "health-read_health_db": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Health"];
                };
            };
        };
    };
    "auth-signup": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["Credentials"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    "auth-login": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["Credentials"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    "auth-logout": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    "auth-logout_all": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    "auth-change_password": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PasswordChange"];
            };
        };
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    "auth-read_me": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserRead"];
                };
            };
        };
    };
    "workspaces-list_workspaces": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WorkspaceRead"][];
                };
            };
        };
    };
    "workspaces-create_workspace_route": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["WorkspaceCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WorkspaceRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    "workspaces-read_workspace": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                workspace_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WorkspaceRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    "workspaces-delete_workspace": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                workspace_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    "workspaces-update_workspace": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                workspace_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["WorkspaceUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WorkspaceRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    "workspaces-leave_workspace": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                workspace_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    "workspaces-list_members": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                workspace_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MemberRead"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    "workspaces-remove_member": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                member_id: string;
                workspace_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    "workspaces-update_member": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                member_id: string;
                workspace_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MemberUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MemberRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    "workspaces-list_invites": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                workspace_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["InviteRead"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    "workspaces-create_invite": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                workspace_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["InviteCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["InviteRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    "workspaces-revoke_invite": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                invite_id: string;
                workspace_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    "invites-read_invite": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                token: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["InvitePreview"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    "invites-accept_invite": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                token: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WorkspaceRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    "companies-list_companies": {
        parameters: {
            query?: {
                limit?: number;
                offset?: number;
                /** @description Matches name, website, or industry. */
                q?: string | null;
            };
            header?: never;
            path: {
                workspace_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CompanyRead"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    "companies-create_company": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                workspace_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CompanyCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CompanyRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    "companies-read_company": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                company_id: string;
                workspace_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CompanyRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    "companies-delete_company": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                company_id: string;
                workspace_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    "companies-update_company": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                company_id: string;
                workspace_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CompanyUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CompanyRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    "companies-list_company_contacts": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                company_id: string;
                workspace_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ContactRead"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    "contacts-list_contacts": {
        parameters: {
            query?: {
                limit?: number;
                offset?: number;
                /** @description Matches name, email, phone, job title, or company. */
                q?: string | null;
                status?: components["schemas"]["ContactStatus"] | null;
                company_id?: string | null;
            };
            header?: never;
            path: {
                workspace_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ContactRead"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    "contacts-create_contact": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                workspace_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ContactCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ContactRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    "contacts-read_contact": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                contact_id: string;
                workspace_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ContactRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    "contacts-delete_contact": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                contact_id: string;
                workspace_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    "contacts-update_contact": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                contact_id: string;
                workspace_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ContactUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ContactRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    "contacts-list_activities": {
        parameters: {
            query?: {
                limit?: number;
                offset?: number;
            };
            header?: never;
            path: {
                contact_id: string;
                workspace_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ActivityRead"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    "contacts-create_activity": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                contact_id: string;
                workspace_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ActivityCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ActivityRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    "tasks-list_tasks": {
        parameters: {
            query?: {
                limit?: number;
                offset?: number;
                due?: components["schemas"]["DueFilter"] | null;
                /** @description IANA time zone that defines 'today'. */
                tz?: string;
                status?: components["schemas"]["TaskStatus"] | null;
                contact_id?: string | null;
                company_id?: string | null;
            };
            header?: never;
            path: {
                workspace_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TaskRead"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    "tasks-create_task": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                workspace_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TaskCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TaskRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    "tasks-read_task": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                task_id: string;
                workspace_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TaskRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    "tasks-delete_task": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                task_id: string;
                workspace_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    "tasks-update_task": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                task_id: string;
                workspace_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TaskUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TaskRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    "dashboard-read_dashboard": {
        parameters: {
            query?: {
                /** @description IANA time zone that defines 'today'. */
                tz?: string;
                /** @description Days without contact that count as stale. */
                stale_days?: number;
                /** @description Size of each contact list. */
                limit?: number;
            };
            header?: never;
            path: {
                workspace_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Dashboard"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_root: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: string;
                    };
                };
            };
        };
    };
}
