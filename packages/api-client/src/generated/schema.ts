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
    "/health/storage": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Read Health Storage
         * @description Readiness: the object store answers and the bucket exists.
         */
        get: operations["health-read_health_storage"];
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
         * @description Create an account, log in, and email a verification link. Until it is
         *     followed, the account can only use `/auth/*`. No workspace: onboarding creates
         *     one, or an invitation is accepted.
         *
         *     With an `invite_token` for this email, no verification link is sent: accepting
         *     the invitation verifies the address.
         */
        post: operations["auth-signup"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/auth/verify-email": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Verify Email
         * @description Follow the emailed link. No login needed: the link may be opened anywhere.
         *
         *     404 for an unknown or already used token; 410 for an expired one.
         */
        post: operations["auth-verify_email"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/auth/resend-verification": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Resend Verification
         * @description Email a new verification link; the previous one stops working.
         */
        post: operations["auth-resend_verification"];
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
        /**
         * Login
         * @description The email counter counts failures only, and a success clears it. Both limits
         *     run before the password hash, which is slow by design.
         */
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
    "/auth/forgot-password": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Forgot Password
         * @description Email a password reset link to the address, if an account has it.
         *
         *     Always 204, so the response does not reveal whether an account exists. A new
         *     request replaces the previous link. The email limit counts unknown addresses
         *     too, for the same reason.
         */
        post: operations["auth-forgot_password"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/auth/reset-password": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Reset Password
         * @description Follow the emailed link: set the password and log in here.
         *
         *     Every existing session is revoked, since whoever asked may have lost control of
         *     one. Following the link proves the address is the user's, so it also counts as
         *     email verification. 404 for an unknown or already used token; 410 for an expired
         *     one.
         */
        post: operations["auth-reset_password"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/auth/change-email": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Change Email
         * @description Email a confirmation link to the new address; the account moves once it is
         *     followed. A new request replaces the pending one.
         *
         *     Allowed before the current address is verified: a typo at signup is the
         *     usual reason to need this. 409 if the address is taken or unchanged.
         */
        post: operations["auth-change_email"];
        /**
         * Cancel Email Change
         * @description Drop the pending change; its link stops working. 204 when there is none too.
         */
        delete: operations["auth-cancel_email_change"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/auth/confirm-email": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Confirm Email
         * @description Follow the link sent to the new address. No login needed: it may be opened
         *     anywhere. Reaching the new inbox proves it, so the account counts as
         *     verified. 404 for an unknown or used token; 410 for an expired one; 409 if
         *     the address was registered meanwhile.
         */
        post: operations["auth-confirm_email"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/auth/delete-account": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Delete Account
         * @description Schedule the account for deletion and log out everywhere.
         *
         *     Logging in within `account_deletion_grace` brings the account back; after
         *     that the purge job removes it, with every workspace the user was alone in.
         *     409 while the user is the only owner of a shared workspace, which would
         *     otherwise be left with nobody to manage it.
         */
        post: operations["auth-delete_account"];
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
        /**
         * Update Me
         * @description Change what the user is called. The email has its own flow: `/change-email`.
         */
        patch: operations["auth-update_me"];
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
         * Create Workspace
         * @description The caller becomes its owner. Starts in onboarding; see `/onboarding/complete`.
         */
        post: operations["workspaces-create_workspace"];
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
         * @description Owners only. Members, invitations, every CRM record, and every stored file go
         *     with it.
         */
        delete: operations["workspaces-delete_workspace"];
        options?: never;
        head?: never;
        /** Update Workspace */
        patch: operations["workspaces-update_workspace"];
        trace?: never;
    };
    "/workspaces/{workspace_id}/onboarding/complete": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Complete Onboarding
         * @description Sets `onboarded_at`. Idempotent.
         */
        post: operations["workspaces-complete_onboarding"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
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
         * @description Pending and declined (`declined_at` set); not accepted, revoked, or expired.
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
    "/workspaces/{workspace_id}/invites/{invite_id}/resend": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Resend Invite
         * @description Email the invitation again with a fresh link; the previous one stops working
         *     and the expiry starts over. Counts against the same limit as sending one.
         */
        post: operations["workspaces-resend_invite"];
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
         * @description The link stops working; a declined invitation leaves the list.
         */
        delete: operations["workspaces-revoke_invite"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/invites/pending": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Pending Invites
         * @description Oldest first.
         */
        get: operations["invites-list_pending_invites"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/invites/pending/{invite_id}/accept": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Accept Pending Invite
         * @description 404 unless pending and addressed to the caller.
         */
        post: operations["invites-accept_pending_invite"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/invites/pending/{invite_id}/decline": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Decline Pending Invite
         * @description The link stops working; the workspace's admins see the refusal.
         */
        post: operations["invites-decline_pending_invite"];
        delete?: never;
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
         *     404 for an unknown, revoked, declined, or used token; 410 for an expired one.
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
         *
         *     The token reached the invitee's inbox, so accepting also proves the account
         *     owns that address: an unverified account is marked verified here.
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
         * @description Sorted by name unless `sort` says otherwise; companies without a value for the
         *     sort column come last either way.
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
         * @description Contacts and tasks at the company are kept, with the link cleared; its
         *     attachments go with it.
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
        /**
         * List Company Contacts
         * @description Sorted by name. `GET .../contacts/?company_id=` is the same list with filters
         *     and sorting.
         */
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
         * @description Sorted by name unless `sort` says otherwise; contacts without a value for the
         *     sort column come last either way.
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
         * @description The contact's activities and attachments go with it; tasks are kept, with the
         *     link cleared.
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
         * @description Soonest due first unless `sort` says otherwise; tasks without a value for the
         *     sort column (undated, or with no contact or company) come last either way.
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
    "/workspaces/{workspace_id}/contacts/{contact_id}/attachments": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Contact Attachments
         * @description Newest first. Files whose upload never completed are left out.
         */
        get: operations["attachments-list_contact_attachments"];
        put?: never;
        /**
         * Create Contact Attachment
         * @description Start an upload: the row is created and an upload URL returned. 413 when
         *     `size` is over the limit.
         */
        post: operations["attachments-create_contact_attachment"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workspaces/{workspace_id}/companies/{company_id}/attachments": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Company Attachments
         * @description Newest first. Files whose upload never completed are left out.
         */
        get: operations["attachments-list_company_attachments"];
        put?: never;
        /**
         * Create Company Attachment
         * @description Start an upload: the row is created and an upload URL returned. 413 when
         *     `size` is over the limit.
         */
        post: operations["attachments-create_company_attachment"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workspaces/{workspace_id}/attachments/{attachment_id}/complete": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Complete Attachment
         * @description Called after the `PUT`. 409 when the object is not in the store yet; 413, and
         *     the object is removed, when it is bigger than allowed. Repeating it is harmless.
         */
        post: operations["attachments-complete_attachment"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workspaces/{workspace_id}/attachments/{attachment_id}/download": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Download Attachment
         * @description Redirects to a short-lived URL that serves the file as a download.
         */
        get: operations["attachments-download_attachment"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workspaces/{workspace_id}/attachments/{attachment_id}": {
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
         * Delete Attachment
         * @description Removes the row, then the file from the store.
         */
        delete: operations["attachments-delete_attachment"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workspaces/{workspace_id}/imports/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Imports
         * @description Newest first, whatever their state.
         */
        get: operations["imports-list_imports"];
        put?: never;
        /**
         * Create Import
         * @description Start an import: the row is created and an upload URL for the CSV returned.
         *     413 when `size` is over the limit.
         */
        post: operations["imports-create_import"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workspaces/{workspace_id}/imports/{import_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Import */
        get: operations["imports-read_import"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workspaces/{workspace_id}/imports/{import_id}/start": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Start Import
         * @description Called after the `PUT`: queues the job. 409 when the file is not in the store
         *     yet or the import was already started; 413, and the file is removed, when it is
         *     bigger than allowed.
         */
        post: operations["imports-start_import"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workspaces/{workspace_id}/assistant/conversations/{conversation_id}/uploads": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Create Upload
         * @description Start a chat upload: the row is created and an upload URL returned. Same size
         *     limit as attachments; 413 above it.
         */
        post: operations["assistant-create_upload"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workspaces/{workspace_id}/assistant/uploads/{upload_id}/complete": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Complete Upload
         * @description Called after the `PUT`. 409 when the object is not in the store yet; 413, and
         *     the object removed, when it is bigger than allowed. Repeating it is harmless.
         */
        post: operations["assistant-complete_upload"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workspaces/{workspace_id}/assistant/uploads/{upload_id}": {
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
         * Delete Upload
         * @description Discard a chat upload the user removed before sending: the row and the
         *     object. 409 once it has become an attachment, which owns the object then.
         */
        delete: operations["assistant-delete_upload"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workspaces/{workspace_id}/assistant/conversations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Conversations
         * @description The caller's conversations in this workspace, most recently active first.
         */
        get: operations["assistant-list_conversations"];
        put?: never;
        /**
         * Create Conversation
         * @description A new, empty conversation. An existing one with no messages is returned
         *     instead, so "New chat" pressed twice does not pile up empty rows.
         */
        post: operations["assistant-create_conversation"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workspaces/{workspace_id}/assistant/conversations/{conversation_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Conversation
         * @description The conversation with its transcript as `UIMessage`s. A tool call still
         *     waiting for approval comes back in the `approval-requested` state.
         */
        get: operations["assistant-get_conversation"];
        put?: never;
        post?: never;
        /**
         * Delete Conversation
         * @description Removes the transcript and the chat's files that were never attached to a
         *     record. Attachments made from the chat stay on their records.
         */
        delete: operations["assistant-delete_conversation"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/workspaces/{workspace_id}/assistant/conversations/{conversation_id}/messages": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Send Message
         * @description Send a message, retry the last reply, or answer an approval request, and
         *     stream the assistant's reply as server-sent events (the Vercel AI data-stream
         *     protocol; `useChat` reads it).
         *
         *     The body is what `useChat` sends. Only its last message is used: a `user`
         *     message is the new turn (files go as `upload_ids` in its `metadata`), an
         *     `assistant` message carries approval responses. `trigger: regenerate-message`
         *     repeats the last user turn. 503 when no model is configured, 429 past the
         *     per-user limit.
         */
        post: operations["assistant-send_message"];
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
        /** AccountDeletion */
        AccountDeletion: {
            /** Current Password */
            current_password: string;
        };
        /** ActivityCreate */
        ActivityCreate: {
            type: components["schemas"]["ActivityType"];
            /** Notes */
            notes?: string | null;
        };
        /** ActivityResponse */
        ActivityResponse: {
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
            /** @description Who logged it; for `task_completed`, who completed the task. */
            created_by: components["schemas"]["UserRef"] | null;
            /** @description Set when the assistant logged it. */
            source: components["schemas"]["RowSource"] | null;
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
        /**
         * AttachmentCreate
         * @description What the client knows before uploading. `size` is checked against the limit
         *     here and again against the stored object on completion.
         */
        AttachmentCreate: {
            /** Filename */
            filename: string;
            /** Content Type */
            content_type: string;
            /**
             * Size
             * @description Bytes.
             */
            size: number;
        };
        /** AttachmentResponse */
        AttachmentResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Contact Id */
            contact_id: string | null;
            /** Company Id */
            company_id: string | null;
            /** Filename */
            filename: string;
            /** Content Type */
            content_type: string;
            /** Size */
            size: number;
            uploaded_by: components["schemas"]["UserRef"] | null;
            /** Uploaded At */
            uploaded_at: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /**
         * AttachmentUpload
         * @description Step one of an upload: `PUT` the file to `upload_url` with the `Content-Type`
         *     and `size` given at creation (the URL accepts nothing else), then
         *     `POST .../attachments/{id}/complete`.
         */
        AttachmentUpload: {
            attachment: components["schemas"]["AttachmentResponse"];
            /** Upload Url */
            upload_url: string;
            /**
             * Expires At
             * Format: date-time
             */
            expires_at: string;
        };
        /**
         * ChatMessageRequest
         * @description What `useChat` posts: the chat id, the trigger, and the messages the browser
         *     has. Only the last message is read; the server holds the history. `tz` is the
         *     user's IANA time zone.
         */
        ChatMessageRequest: {
            /** Id */
            id?: string | null;
            /**
             * Trigger
             * @default submit-message
             */
            trigger: string;
            /** Messages */
            messages: {
                [key: string]: unknown;
            }[];
            /** Tz */
            tz?: string | null;
            /** Messageid */
            messageId?: string | null;
        } & {
            [key: string]: unknown;
        };
        /**
         * ChatUploadCreate
         * @description What the browser knows before uploading a file into the chat.
         */
        ChatUploadCreate: {
            /** Filename */
            filename: string;
            /** Content Type */
            content_type: string;
            /**
             * Size
             * @description Bytes.
             */
            size: number;
        };
        /** ChatUploadResponse */
        ChatUploadResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Conversation Id
             * Format: uuid
             */
            conversation_id: string;
            /** Filename */
            filename: string;
            /** Content Type */
            content_type: string;
            /** Size */
            size: number;
            /** Uploaded At */
            uploaded_at: string | null;
            /** Attachment Id */
            attachment_id: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /**
         * ChatUploadTicket
         * @description Step one of a chat upload: `PUT` the file to `upload_url` with the
         *     `Content-Type` and `size` given at creation, then `POST .../uploads/{id}/complete`.
         */
        ChatUploadTicket: {
            upload: components["schemas"]["ChatUploadResponse"];
            /** Upload Url */
            upload_url: string;
            /**
             * Expires At
             * Format: date-time
             */
            expires_at: string;
        };
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
        /** CompanyRef */
        CompanyRef: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
        };
        /** CompanyResponse */
        CompanyResponse: {
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
            created_by: components["schemas"]["UserRef"] | null;
            /** @description Set when the assistant or an import made the row. */
            source: components["schemas"]["RowSource"] | null;
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
         * CompanySort
         * @enum {string}
         */
        CompanySort: "name" | "industry" | "created_at";
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
        /** ContactResponse */
        ContactResponse: {
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
            created_by: components["schemas"]["UserRef"] | null;
            /** @description Set when the assistant or an import made the row. */
            source: components["schemas"]["RowSource"] | null;
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
         * ContactSort
         * @enum {string}
         */
        ContactSort: "name" | "company" | "status" | "last_contacted_at";
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
        /** ConversationDetailResponse */
        ConversationDetailResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Title
             * @description Null until the first message names it.
             */
            title: string | null;
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
            /**
             * Messages
             * @description The transcript as Vercel AI SDK `UIMessage`s, for `useChat`.
             */
            messages: {
                [key: string]: unknown;
            }[];
        };
        /** ConversationResponse */
        ConversationResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Title
             * @description Null until the first message names it.
             */
            title: string | null;
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
        /** DashboardResponse */
        DashboardResponse: {
            /** Total Contacts */
            total_contacts: number;
            /** Tasks Due Today */
            tasks_due_today: number;
            /** Overdue Tasks */
            overdue_tasks: number;
            /** Recently Contacted */
            recently_contacted: components["schemas"]["ContactResponse"][];
            /** Not Recently Contacted */
            not_recently_contacted: components["schemas"]["ContactResponse"][];
        };
        /**
         * DueFilter
         * @enum {string}
         */
        DueFilter: "overdue" | "today" | "upcoming";
        /** EmailChangeConfirmation */
        EmailChangeConfirmation: {
            /** Token */
            token: string;
        };
        /** EmailChangeRequest */
        EmailChangeRequest: {
            /**
             * New Email
             * Format: email
             */
            new_email: string;
            /** Current Password */
            current_password: string;
        };
        /**
         * EmailVerification
         * @description The token from the verification link.
         */
        EmailVerification: {
            /** Token */
            token: string;
        };
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
        /**
         * ImportCreate
         * @description What the client knows before uploading the CSV.
         */
        ImportCreate: {
            kind: components["schemas"]["ImportKind"];
            /** Filename */
            filename: string;
            /**
             * Size
             * @description Bytes.
             */
            size: number;
        };
        /**
         * ImportKind
         * @enum {string}
         */
        ImportKind: "contacts" | "companies";
        /** ImportResponse */
        ImportResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            kind: components["schemas"]["ImportKind"];
            status: components["schemas"]["ImportStatus"];
            /** Filename */
            filename: string;
            /** Size */
            size: number;
            requested_by: components["schemas"]["UserRef"] | null;
            /** Started At */
            started_at: string | null;
            /** Finished At */
            finished_at: string | null;
            /** Total Rows */
            total_rows: number;
            /** Created Count */
            created_count: number;
            /** Skipped Count */
            skipped_count: number;
            /** Failed Count */
            failed_count: number;
            /** Errors */
            errors: components["schemas"]["RowError"][];
            /**
             * Error
             * @description Why the import could not finish, if it could not.
             */
            error: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /**
         * ImportStatus
         * @description `pending` until the client reports the CSV uploaded, `queued` once the job is
         *     sent, `running` while the worker reads the file, then `done` or `failed`.
         * @enum {string}
         */
        ImportStatus: "pending" | "queued" | "running" | "done" | "failed";
        /**
         * ImportUpload
         * @description Step one of an import: `PUT` the CSV to `upload_url` as `text/csv` with the
         *     `size` given at creation, then `POST .../imports/{id}/start`.
         */
        ImportUpload: {
            import: components["schemas"]["ImportResponse"];
            /** Upload Url */
            upload_url: string;
            /**
             * Expires At
             * Format: date-time
             */
            expires_at: string;
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
        /**
         * InviteResponse
         * @description As the workspace's admins see it: pending, or declined by the invitee.
         */
        InviteResponse: {
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
            /** Declined At */
            declined_at: string | null;
        };
        /** MemberResponse */
        MemberResponse: {
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
        /** ActivityResponsePage */
        PageOf_ActivityResponse_: {
            /** Items */
            items: components["schemas"]["ActivityResponse"][];
            /**
             * Total
             * @description Rows matching the filters, across every page.
             */
            total: number;
            /** Limit */
            limit: number;
            /** Offset */
            offset: number;
        };
        /** AttachmentResponsePage */
        PageOf_AttachmentResponse_: {
            /** Items */
            items: components["schemas"]["AttachmentResponse"][];
            /**
             * Total
             * @description Rows matching the filters, across every page.
             */
            total: number;
            /** Limit */
            limit: number;
            /** Offset */
            offset: number;
        };
        /** CompanyResponsePage */
        PageOf_CompanyResponse_: {
            /** Items */
            items: components["schemas"]["CompanyResponse"][];
            /**
             * Total
             * @description Rows matching the filters, across every page.
             */
            total: number;
            /** Limit */
            limit: number;
            /** Offset */
            offset: number;
        };
        /** ContactResponsePage */
        PageOf_ContactResponse_: {
            /** Items */
            items: components["schemas"]["ContactResponse"][];
            /**
             * Total
             * @description Rows matching the filters, across every page.
             */
            total: number;
            /** Limit */
            limit: number;
            /** Offset */
            offset: number;
        };
        /** ImportResponsePage */
        PageOf_ImportResponse_: {
            /** Items */
            items: components["schemas"]["ImportResponse"][];
            /**
             * Total
             * @description Rows matching the filters, across every page.
             */
            total: number;
            /** Limit */
            limit: number;
            /** Offset */
            offset: number;
        };
        /** TaskResponsePage */
        PageOf_TaskResponse_: {
            /** Items */
            items: components["schemas"]["TaskResponse"][];
            /**
             * Total
             * @description Rows matching the filters, across every page.
             */
            total: number;
            /** Limit */
            limit: number;
            /** Offset */
            offset: number;
        };
        /** PasswordChange */
        PasswordChange: {
            /** Current Password */
            current_password: string;
            /** New Password */
            new_password: string;
        };
        /**
         * PasswordReset
         * @description The token from the reset link, and the password to set.
         */
        PasswordReset: {
            /** Token */
            token: string;
            /** New Password */
            new_password: string;
        };
        /** PasswordResetRequest */
        PasswordResetRequest: {
            /**
             * Email
             * Format: email
             */
            email: string;
        };
        /**
         * PendingInviteResponse
         * @description One of the caller's own, by id: the token is not stored, so this is how the
         *     app accepts or declines one without the link.
         */
        PendingInviteResponse: {
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
            /**
             * Id
             * Format: uuid
             */
            id: string;
        };
        /**
         * Permission
         * @enum {string}
         */
        Permission: "crm:read" | "crm:write" | "members:read" | "members:manage" | "workspace:manage" | "workspace:delete";
        /** ProfileUpdate */
        ProfileUpdate: {
            /** Name */
            name: string;
        };
        /** RowError */
        RowError: {
            /**
             * Row
             * @description Line number in the file; the header is line 1.
             */
            row: number;
            /** Message */
            message: string;
        };
        /**
         * RowSource
         * @description How a row came to be, when not typed in by hand: the assistant or a CSV import.
         *     Null for rows made in the UI.
         * @enum {string}
         */
        RowSource: "agent" | "import";
        /** Signup */
        Signup: {
            /**
             * Email
             * Format: email
             */
            email: string;
            /** Password */
            password: string;
            /** Name */
            name: string;
            /** Invite Token */
            invite_token?: string | null;
        };
        /**
         * SortOrder
         * @enum {string}
         */
        SortOrder: "asc" | "desc";
        /** TaskCreate */
        TaskCreate: {
            /** Title */
            title: string;
            /** Due At */
            due_at?: string | null;
            /** @default open */
            status: components["schemas"]["TaskStatus"];
            /**
             * Contact Id
             * @description Links the task to a person.
             */
            contact_id?: string | null;
            /**
             * Company Id
             * @description Links the task to a company with no particular person.
             */
            company_id?: string | null;
            /** Notes */
            notes?: string | null;
        };
        /** TaskResponse */
        TaskResponse: {
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
            /** @description The company the task is about: its own, or its contact's. */
            company: components["schemas"]["CompanyRef"] | null;
            created_by: components["schemas"]["UserRef"] | null;
            /** @description Set when the assistant or an import made the row. */
            source: components["schemas"]["RowSource"] | null;
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
         * TaskSort
         * @enum {string}
         */
        TaskSort: "due_at" | "title" | "contact" | "company";
        /**
         * TaskStatus
         * @enum {string}
         */
        TaskStatus: "open" | "done";
        /**
         * TaskUpdate
         * @description Setting `contact_id` unlinks the company and vice versa: the link moves.
         */
        TaskUpdate: {
            /** Title */
            title?: string | null;
            /** Due At */
            due_at?: string | null;
            status?: components["schemas"]["TaskStatus"] | null;
            /**
             * Contact Id
             * @description Links the task to a person.
             */
            contact_id?: string | null;
            /**
             * Company Id
             * @description Links the task to a company with no particular person.
             */
            company_id?: string | null;
            /** Notes */
            notes?: string | null;
        };
        /** UserRef */
        UserRef: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Email */
            email: string;
        };
        /** UserResponse */
        UserResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Email */
            email: string;
            /** Name */
            name: string;
            /** Email Verified At */
            email_verified_at: string | null;
            /** Pending Email */
            pending_email: string | null;
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
         * WorkspaceResponse
         * @description A workspace as seen by one member: their role and what it allows come along.
         */
        WorkspaceResponse: {
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
            /** Onboarded At */
            onboarded_at: string | null;
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
export type AccountDeletion = components['schemas']['AccountDeletion'];
export type ActivityCreate = components['schemas']['ActivityCreate'];
export type ActivityResponse = components['schemas']['ActivityResponse'];
export type ActivityType = components['schemas']['ActivityType'];
export type AttachmentCreate = components['schemas']['AttachmentCreate'];
export type AttachmentResponse = components['schemas']['AttachmentResponse'];
export type AttachmentUpload = components['schemas']['AttachmentUpload'];
export type ChatMessageRequest = components['schemas']['ChatMessageRequest'];
export type ChatUploadCreate = components['schemas']['ChatUploadCreate'];
export type ChatUploadResponse = components['schemas']['ChatUploadResponse'];
export type ChatUploadTicket = components['schemas']['ChatUploadTicket'];
export type CompanyCreate = components['schemas']['CompanyCreate'];
export type CompanyRef = components['schemas']['CompanyRef'];
export type CompanyResponse = components['schemas']['CompanyResponse'];
export type CompanySort = components['schemas']['CompanySort'];
export type CompanyUpdate = components['schemas']['CompanyUpdate'];
export type ContactCreate = components['schemas']['ContactCreate'];
export type ContactRef = components['schemas']['ContactRef'];
export type ContactResponse = components['schemas']['ContactResponse'];
export type ContactSort = components['schemas']['ContactSort'];
export type ContactStatus = components['schemas']['ContactStatus'];
export type ContactUpdate = components['schemas']['ContactUpdate'];
export type ConversationDetailResponse = components['schemas']['ConversationDetailResponse'];
export type ConversationResponse = components['schemas']['ConversationResponse'];
export type Credentials = components['schemas']['Credentials'];
export type DashboardResponse = components['schemas']['DashboardResponse'];
export type DueFilter = components['schemas']['DueFilter'];
export type EmailChangeConfirmation = components['schemas']['EmailChangeConfirmation'];
export type EmailChangeRequest = components['schemas']['EmailChangeRequest'];
export type EmailVerification = components['schemas']['EmailVerification'];
export type HttpValidationError = components['schemas']['HTTPValidationError'];
export type Health = components['schemas']['Health'];
export type ImportCreate = components['schemas']['ImportCreate'];
export type ImportKind = components['schemas']['ImportKind'];
export type ImportResponse = components['schemas']['ImportResponse'];
export type ImportStatus = components['schemas']['ImportStatus'];
export type ImportUpload = components['schemas']['ImportUpload'];
export type InviteCreate = components['schemas']['InviteCreate'];
export type InvitePreview = components['schemas']['InvitePreview'];
export type InviteResponse = components['schemas']['InviteResponse'];
export type MemberResponse = components['schemas']['MemberResponse'];
export type MemberUpdate = components['schemas']['MemberUpdate'];
export type PageOfActivityResponse = components['schemas']['PageOf_ActivityResponse_'];
export type PageOfAttachmentResponse = components['schemas']['PageOf_AttachmentResponse_'];
export type PageOfCompanyResponse = components['schemas']['PageOf_CompanyResponse_'];
export type PageOfContactResponse = components['schemas']['PageOf_ContactResponse_'];
export type PageOfImportResponse = components['schemas']['PageOf_ImportResponse_'];
export type PageOfTaskResponse = components['schemas']['PageOf_TaskResponse_'];
export type PasswordChange = components['schemas']['PasswordChange'];
export type PasswordReset = components['schemas']['PasswordReset'];
export type PasswordResetRequest = components['schemas']['PasswordResetRequest'];
export type PendingInviteResponse = components['schemas']['PendingInviteResponse'];
export type Permission = components['schemas']['Permission'];
export type ProfileUpdate = components['schemas']['ProfileUpdate'];
export type RowError = components['schemas']['RowError'];
export type RowSource = components['schemas']['RowSource'];
export type Signup = components['schemas']['Signup'];
export type SortOrder = components['schemas']['SortOrder'];
export type TaskCreate = components['schemas']['TaskCreate'];
export type TaskResponse = components['schemas']['TaskResponse'];
export type TaskSort = components['schemas']['TaskSort'];
export type TaskStatus = components['schemas']['TaskStatus'];
export type TaskUpdate = components['schemas']['TaskUpdate'];
export type UserRef = components['schemas']['UserRef'];
export type UserResponse = components['schemas']['UserResponse'];
export type ValidationError = components['schemas']['ValidationError'];
export type WorkspaceCreate = components['schemas']['WorkspaceCreate'];
export type WorkspaceResponse = components['schemas']['WorkspaceResponse'];
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
    "health-read_health_storage": {
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
                "application/json": components["schemas"]["Signup"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserResponse"];
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
    "auth-verify_email": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["EmailVerification"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserResponse"];
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
    "auth-resend_verification": {
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
                    "application/json": components["schemas"]["UserResponse"];
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
    "auth-forgot_password": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PasswordResetRequest"];
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
    "auth-reset_password": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PasswordReset"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserResponse"];
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
    "auth-change_email": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["EmailChangeRequest"];
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
    "auth-cancel_email_change": {
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
    "auth-confirm_email": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["EmailChangeConfirmation"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserResponse"];
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
    "auth-delete_account": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AccountDeletion"];
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
                    "application/json": components["schemas"]["UserResponse"];
                };
            };
        };
    };
    "auth-update_me": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProfileUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserResponse"];
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
                    "application/json": components["schemas"]["WorkspaceResponse"][];
                };
            };
        };
    };
    "workspaces-create_workspace": {
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
                    "application/json": components["schemas"]["WorkspaceResponse"];
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
                    "application/json": components["schemas"]["WorkspaceResponse"];
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
                    "application/json": components["schemas"]["WorkspaceResponse"];
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
    "workspaces-complete_onboarding": {
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
                    "application/json": components["schemas"]["WorkspaceResponse"];
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
                    "application/json": components["schemas"]["MemberResponse"][];
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
                    "application/json": components["schemas"]["MemberResponse"];
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
                    "application/json": components["schemas"]["InviteResponse"][];
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
                    "application/json": components["schemas"]["InviteResponse"];
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
    "workspaces-resend_invite": {
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
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["InviteResponse"];
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
    "invites-list_pending_invites": {
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
                    "application/json": components["schemas"]["PendingInviteResponse"][];
                };
            };
        };
    };
    "invites-accept_pending_invite": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                invite_id: string;
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
                    "application/json": components["schemas"]["WorkspaceResponse"];
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
    "invites-decline_pending_invite": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                invite_id: string;
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
                    "application/json": components["schemas"]["WorkspaceResponse"];
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
                sort?: components["schemas"]["CompanySort"];
                order?: components["schemas"]["SortOrder"];
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
                    "application/json": components["schemas"]["PageOf_CompanyResponse_"];
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
                    "application/json": components["schemas"]["CompanyResponse"];
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
                    "application/json": components["schemas"]["CompanyResponse"];
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
                    "application/json": components["schemas"]["CompanyResponse"];
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
            query?: {
                limit?: number;
                offset?: number;
            };
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
                    "application/json": components["schemas"]["PageOf_ContactResponse_"];
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
                sort?: components["schemas"]["ContactSort"];
                order?: components["schemas"]["SortOrder"];
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
                    "application/json": components["schemas"]["PageOf_ContactResponse_"];
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
                    "application/json": components["schemas"]["ContactResponse"];
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
                    "application/json": components["schemas"]["ContactResponse"];
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
                    "application/json": components["schemas"]["ContactResponse"];
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
                    "application/json": components["schemas"]["PageOf_ActivityResponse_"];
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
                    "application/json": components["schemas"]["ActivityResponse"];
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
                /** @description Tasks linked to the company, or to one of its contacts. */
                company_id?: string | null;
                sort?: components["schemas"]["TaskSort"];
                order?: components["schemas"]["SortOrder"];
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
                    "application/json": components["schemas"]["PageOf_TaskResponse_"];
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
                    "application/json": components["schemas"]["TaskResponse"];
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
                    "application/json": components["schemas"]["TaskResponse"];
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
                    "application/json": components["schemas"]["TaskResponse"];
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
                    "application/json": components["schemas"]["DashboardResponse"];
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
    "attachments-list_contact_attachments": {
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
                    "application/json": components["schemas"]["PageOf_AttachmentResponse_"];
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
    "attachments-create_contact_attachment": {
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
                "application/json": components["schemas"]["AttachmentCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AttachmentUpload"];
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
    "attachments-list_company_attachments": {
        parameters: {
            query?: {
                limit?: number;
                offset?: number;
            };
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
                    "application/json": components["schemas"]["PageOf_AttachmentResponse_"];
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
    "attachments-create_company_attachment": {
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
                "application/json": components["schemas"]["AttachmentCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AttachmentUpload"];
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
    "attachments-complete_attachment": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                attachment_id: string;
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
                    "application/json": components["schemas"]["AttachmentResponse"];
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
    "attachments-download_attachment": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                attachment_id: string;
                workspace_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            307: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
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
    "attachments-delete_attachment": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                attachment_id: string;
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
    "imports-list_imports": {
        parameters: {
            query?: {
                limit?: number;
                offset?: number;
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
                    "application/json": components["schemas"]["PageOf_ImportResponse_"];
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
    "imports-create_import": {
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
                "application/json": components["schemas"]["ImportCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ImportUpload"];
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
    "imports-read_import": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                import_id: string;
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
                    "application/json": components["schemas"]["ImportResponse"];
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
    "imports-start_import": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                import_id: string;
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
                    "application/json": components["schemas"]["ImportResponse"];
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
    "assistant-create_upload": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                conversation_id: string;
                workspace_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ChatUploadCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ChatUploadTicket"];
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
    "assistant-complete_upload": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                upload_id: string;
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
                    "application/json": components["schemas"]["ChatUploadResponse"];
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
    "assistant-delete_upload": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                upload_id: string;
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
    "assistant-list_conversations": {
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
                    "application/json": components["schemas"]["ConversationResponse"][];
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
    "assistant-create_conversation": {
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
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConversationResponse"];
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
    "assistant-get_conversation": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                conversation_id: string;
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
                    "application/json": components["schemas"]["ConversationDetailResponse"];
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
    "assistant-delete_conversation": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                conversation_id: string;
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
    "assistant-send_message": {
        parameters: {
            query?: never;
            header?: never;
            path: {
                conversation_id: string;
                workspace_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ChatMessageRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "text/event-stream": string;
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
