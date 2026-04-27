# -*- coding: utf-8 -*-
from markupsafe import Markup
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrLeaveInherit(models.Model):
    _inherit = "hr.leave"

    # =========================================================================
    # Approval flows by requester role
    #
    #   Employee       →  submitted → branch_approved → manager_approved → hr_approved → approved
    #   Officer        →  submitted → manager_approved (respective manager) → hr_approved → approved
    #   Branch Manager →  submitted → manager_approved → hr_approved → approved
    #   Manager        →  submitted → ceo_approved → hr_approved → approved
    #   HR             →  submitted → ceo_approved → hr_approved (self) → approved
    #
    # =========================================================================
    approval_state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("branch_approved", "Branch Manager"),
            ("manager_approved", "Manager"),
            ("ceo_approved", "CEO"),
            ("hr_approved", "HR"),
            ("approved", "Approved"),
            ("refused", "Refused"),
        ],
        string="Approval Status",
        default="draft",
        tracking=True,
        copy=False,
        index=True,
    )

    # Stored at submit time — drives all downstream routing
    requester_role = fields.Selection(
        selection=[
            ("employee", "Employee"),
            ("officer", "Officer"),
            ("branch_manager", "Branch Manager"),
            ("manager", "Manager"),
            ("hr", "HR"),
        ],
        string="Requester Role",
        readonly=True,
        copy=False,
        index=True,
    )

    request_date_from = fields.Date(string="Request Start Date", readonly=False)
    request_date_to = fields.Date(string="Request End Date", readonly=False)

    # -------------------------------------------------------------------------
    # Role helpers
    # -------------------------------------------------------------------------
    def _is_officer(self):
        return self.env.user.has_group("time_off_roles.group_timeoff_officer")

    def _is_branch_manager(self):
        return self.env.user.has_group("time_off_roles.group_timeoff_branch_manager")

    def _is_manager(self):
        return self.env.user.has_group("time_off_roles.group_timeoff_manager")

    def _is_ceo(self):
        return self.env.user.has_group("time_off_roles.group_timeoff_ceo")

    def _is_hr(self):
        return self.env.user.has_group("time_off_roles.group_timeoff_hr")

    def _is_own_leave(self, leave):
        return leave.employee_id and leave.employee_id.user_id == self.env.user

    def _is_respective_manager(self, leave):
        """Check if current user is the respective manager (parent_id) of the employee"""
        if not leave.employee_id or not leave.employee_id.parent_id:
            return False
        return leave.employee_id.parent_id.user_id == self.env.user

    def _get_requester_role(self):
        """Detect the role of the person submitting the request (highest role wins)."""
        user = self.env.user
        if user.has_group("time_off_roles.group_timeoff_hr"):
            return "hr"
        if user.has_group("time_off_roles.group_timeoff_manager"):
            return "manager"
        if user.has_group("time_off_roles.group_timeoff_branch_manager"):
            return "branch_manager"
        if user.has_group("time_off_roles.group_timeoff_officer"):
            return "officer"
        return "employee"

    def _check_no_employee(self):
        for leave in self:
            if not leave.employee_id:
                raise UserError(
                    _(
                        "Your user account is not linked to any employee in "
                        "this company.\n\nPlease ask your HR administrator to "
                        "open your employee record and set your user in the "
                        "'Related User' field."
                    )
                )

    def _state_label(self, leave, state):
        return dict(leave._fields["approval_state"].selection).get(state, state)

    # -------------------------------------------------------------------------
    # In-app notification helper
    # -------------------------------------------------------------------------
    def _send_inapp_notification(self, user, summary, note):
        if not user or not user.id:
            return
        model_id = self.env["ir.model"]._get_id("hr.leave")
        self.env["mail.activity"].sudo().create(
            {
                "res_id": self.id,
                "res_model_id": model_id,
                "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                "user_id": user.id,
                "summary": summary,
                "note": note,
            }
        )

    # -------------------------------------------------------------------------
    # Chatter helpers
    # -------------------------------------------------------------------------
    def _post_approval_message(self, role_label, next_state=None):
        for leave in self:
            if next_state and next_state != "approved":
                next_label = self._state_label(leave, next_state)
                body = Markup(
                    "<p><b>{role} Approved</b><br/>"
                    "{name} ({role}) has approved this leave request.<br/>"
                    "<b>Next Stage:</b> {next}</p>"
                ).format(role=role_label, name=self.env.user.name, next=next_label)
                note = Markup(
                    "<b>{role}</b> approved your leave. Next stage: {next}"
                ).format(role=role_label, next=next_label)
            else:
                body = Markup(
                    "<p><b>Final Approval — {role}</b><br/>"
                    "{name} ({role}) has given final approval. "
                    "Your leave is now <b>Approved</b>.</p>"
                ).format(role=role_label, name=self.env.user.name)
                note = Markup(
                    "<b>{role}</b> has fully approved your leave request."
                ).format(role=role_label)

            leave.with_context(mail_notify_force_send=False).message_post(
                body=body,
                subtype_xmlid="mail.mt_note",
            )
            if leave.employee_id.user_id:
                leave._send_inapp_notification(
                    user=leave.employee_id.user_id,
                    summary=_("%s approved your leave") % role_label,
                    note=note,
                )

    def _post_refusal_message(self, reason):
        for leave in self:
            if reason:
                body = Markup(
                    "<p><b>Leave Request Refused</b><br/>"
                    "{name} has refused this leave request.<br/>"
                    "<b>Reason:</b> {reason}</p>"
                ).format(name=self.env.user.name, reason=reason)
                note = Markup("Your leave was refused. <b>Reason:</b> {reason}").format(
                    reason=reason
                )
            else:
                body = Markup(
                    "<p><b>Leave Request Refused</b><br/>"
                    "{name} has refused this leave request.</p>"
                ).format(name=self.env.user.name)
                note = Markup("Your leave request was refused.")

            leave.with_context(mail_notify_force_send=False).message_post(
                body=body,
                subtype_xmlid="mail.mt_note",
            )
            if leave.employee_id.user_id:
                leave._send_inapp_notification(
                    user=leave.employee_id.user_id,
                    summary=_("Your leave request was refused"),
                    note=note,
                )

    def _post_submit_message(self, next_approver_label):
        for leave in self:
            body = Markup(
                "<p><b>Leave Request Submitted</b><br/>"
                "{name} has submitted a leave request for approval.<br/>"
                "<b>Next Approver:</b> {next}</p>"
            ).format(name=self.env.user.name, next=next_approver_label)
            leave.with_context(mail_notify_force_send=False).message_post(
                body=body,
                subtype_xmlid="mail.mt_note",
            )

    # =========================================================================
    # STEP 1 — Anyone: Submit  (Draft → Submitted)
    # =========================================================================
    def action_submit(self):
        self._check_no_employee()
        for leave in self:
            if leave.approval_state != "draft":
                raise UserError(_("Only draft requests can be submitted."))

            role = self._get_requester_role()
            leave.requester_role = role
            leave.sudo().write({"state": "confirm"})
            leave.approval_state = "submitted"

            # Chatter: tell everyone who approves next
            next_approver_map = {
                "employee": _("Branch Manager"),
                "officer": _("Manager (Respective)"),
                "branch_manager": _("Manager"),
                "manager": _("CEO"),
                "hr": _("CEO"),
            }
            leave._post_submit_message(next_approver_map.get(role, _("Next Approver")))

    # =========================================================================
    # STEP 2 — Branch Manager Approve
    #   Flow : Employee only
    #   Trans: submitted → branch_approved
    # =========================================================================
    def action_approve_branch_manager(self):
        for leave in self:
            if not self._is_branch_manager():
                raise UserError(_("Only a Branch Manager can approve at this stage."))
            if leave.requester_role != "employee":
                raise UserError(
                    _(
                        "Branch Manager approval only applies to employee leave requests."
                    )
                )
            if leave.approval_state != "submitted":
                raise UserError(
                    _(
                        "This leave is not waiting for Branch Manager approval.\n"
                        "Current stage: %s"
                    )
                    % self._state_label(leave, leave.approval_state)
                )
            leave.approval_state = "branch_approved"
        self._post_approval_message(_("Branch Manager"), "manager_approved")

    # =========================================================================
    # STEP 3 — Manager Approve
    #   Flow A (Employee)       : branch_approved  → manager_approved
    #   Flow B (Officer)        : submitted        → manager_approved (respective manager only)
    #   Flow C (Branch Manager) : submitted        → manager_approved
    # =========================================================================
    def action_approve_manager(self):
        for leave in self:
            if not self._is_manager():
                raise UserError(_("Only a Manager can approve at this stage."))

            # Flow A: Employee (requires branch manager approval first)
            if leave.requester_role == "employee":
                if leave.approval_state != "branch_approved":
                    raise UserError(
                        _(
                            "Manager approval requires Branch Manager approval first.\n"
                            "Current stage: %s"
                        )
                        % self._state_label(leave, leave.approval_state)
                    )

            # Flow B: Officer (submitted → manager_approved, respective manager only)
            elif leave.requester_role == "officer":
                if leave.approval_state != "submitted":
                    raise UserError(
                        _(
                            "This leave is not waiting for Manager approval.\n"
                            "Current stage: %s"
                        )
                        % self._state_label(leave, leave.approval_state)
                    )
                # Check if current user is the respective manager (parent_id)
                if not self._is_respective_manager(leave):
                    raise UserError(
                        _(
                            "Only the respective manager can approve this officer's leave request.\n"
                            "Respective Manager: %s"
                        )
                        % (
                            leave.employee_id.parent_id.name
                            if leave.employee_id.parent_id
                            else _("Not Set")
                        )
                    )

            # Flow C: Branch Manager
            elif leave.requester_role == "branch_manager":
                if leave.approval_state != "submitted":
                    raise UserError(
                        _(
                            "This leave is not waiting for Manager approval.\n"
                            "Current stage: %s"
                        )
                        % self._state_label(leave, leave.approval_state)
                    )

            else:
                raise UserError(
                    _(
                        "Manager approval does not apply to this leave request "
                        "(requester role: %s)."
                    )
                    % leave.requester_role
                )

            leave.approval_state = "manager_approved"
        self._post_approval_message(_("Manager"), "hr_approved")

    # =========================================================================
    # STEP 2 (alt) — CEO Approve
    #   Flow : Manager or HR requester
    #   Trans: submitted → ceo_approved
    # =========================================================================
    def action_approve_ceo(self):
        for leave in self:
            if not self._is_ceo():
                raise UserError(_("Only the CEO can approve at this stage."))
            if leave.requester_role not in ("manager", "hr"):
                raise UserError(
                    _("CEO approval only applies to Manager or HR leave requests.")
                )
            if leave.approval_state != "submitted":
                raise UserError(
                    _(
                        "This leave is not waiting for CEO approval.\n"
                        "Current stage: %s"
                    )
                    % self._state_label(leave, leave.approval_state)
                )
            leave.approval_state = "ceo_approved"
        self._post_approval_message(_("CEO"), "hr_approved")

    # =========================================================================
    # FINAL STEP — HR Final Approval  → Approved
    #   Valid prior states: manager_approved  (employee / officer / branch_manager flows)
    #                       ceo_approved      (manager / hr flows)
    # =========================================================================
    def action_validate(self, check_state=True):
        for leave in self:
            if not self._is_hr():
                raise UserError(_("Only HR can give the final approval."))
            if leave.approval_state not in ("manager_approved", "ceo_approved"):
                raise UserError(
                    _(
                        "This leave is not ready for HR final approval yet.\n"
                        "Current stage: %s"
                    )
                    % self._state_label(leave, leave.approval_state)
                )

        result = super().action_validate(check_state)
        for leave in self:
            leave.approval_state = "approved"
        self._post_approval_message(_("HR"))
        return result

    # =========================================================================
    # Refuse
    #   Rule: Refuse button is visible ONLY at the stage where the role can approve.
    #   HR is the exception — HR can refuse at any pending stage.
    # =========================================================================
    def _can_refuse(self, leave):
        """
        Refuse is allowed only when it is exactly that role's turn to approve.
        Mirrors the approve button visibility 1-to-1:

          Branch Manager → state='submitted'        AND requester='employee'
          Manager        → state='branch_approved'  AND requester='employee'
                           OR state='submitted'     AND requester='branch_manager'
                           OR state='submitted'     AND requester='officer' AND is_respective_manager
          CEO            → state='submitted'        AND requester in ('manager','hr')
          HR             → state in ('manager_approved','ceo_approved')
        """
        if leave.approval_state in ("draft", "approved", "refused"):
            return False

        user = self.env.user

        if user.has_group("time_off_roles.group_timeoff_hr"):
            return leave.approval_state in ("manager_approved", "ceo_approved")

        if user.has_group("time_off_roles.group_timeoff_ceo"):
            return leave.approval_state == "submitted" and leave.requester_role in (
                "manager",
                "hr",
            )

        if user.has_group("time_off_roles.group_timeoff_manager"):
            # Employee flow
            if leave.requester_role == "employee":
                return leave.approval_state == "branch_approved"
            # Branch Manager flow
            elif leave.requester_role == "branch_manager":
                return leave.approval_state == "submitted"
            # Officer flow (respective manager only)
            elif leave.requester_role == "officer":
                return (
                    leave.approval_state == "submitted"
                    and self._is_respective_manager(leave)
                )
            return False

        if user.has_group("time_off_roles.group_timeoff_branch_manager"):
            return (
                leave.approval_state == "submitted"
                and leave.requester_role == "employee"
            )

        return False

    def action_refuse(self):
        for leave in self:
            if leave.approval_state in ("draft", "approved", "refused"):
                raise UserError(
                    _("You can only refuse a leave that is currently pending approval.")
                )
            if not self._can_refuse(leave):
                raise UserError(
                    _(
                        "You are not authorised to refuse this leave request at its current stage."
                    )
                )

        return {
            "name": _("Refuse Leave Request"),
            "type": "ir.actions.act_window",
            "res_model": "hr.leave.refuse.reason.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_leave_ids": self.ids},
        }

    def _do_refuse(self, reason):
        for leave in self:
            if leave.approval_state in ("draft", "approved", "refused"):
                raise UserError(
                    _("You can only refuse a leave that is currently pending approval.")
                )
            if not self._can_refuse(leave):
                raise UserError(
                    _(
                        "You are not authorised to refuse this leave request at its current stage."
                    )
                )

        super(HrLeaveInherit, self).action_refuse()
        for leave in self:
            leave.approval_state = "refused"
            if hasattr(leave, "refuse_reason") and reason:
                leave.refuse_reason = reason
        self._post_refusal_message(reason)

    # =========================================================================
    # Reset to Draft  (Refused → Draft)
    # =========================================================================
    def action_reset_to_draft(self):
        for leave in self:
            if leave.approval_state != "refused":
                raise UserError(_("Only refused leaves can be reset to draft."))
            if not self._is_own_leave(leave) and not self._is_hr():
                raise UserError(
                    _(
                        "Only the employee who submitted this leave, or HR, "
                        "can reset it to draft."
                    )
                )
        self.sudo().action_draft()
        for leave in self:
            leave.approval_state = "draft"
            leave.requester_role = False

    # =========================================================================
    # Defaults / onchange helpers
    # =========================================================================
    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if "employee_id" in fields_list and not defaults.get("employee_id"):
            employee = self.env["hr.employee"].search(
                [("user_id", "=", self.env.uid)], limit=1
            )
            if employee:
                defaults["employee_id"] = employee.id
            else:
                is_officer = self.env.user.has_group(
                    "hr_holidays.group_hr_holidays_user"
                ) or self.env.user.has_group("hr_holidays.group_hr_holidays_manager")
                if not is_officer:
                    raise UserError(
                        _(
                            "Your user account is not linked to any employee "
                            "in this company.\n\nPlease ask your HR administrator "
                            "to open your employee record and set your user in "
                            "the 'Related User' field."
                        )
                    )
        return defaults

    @api.onchange("holiday_status_id", "date_from", "date_to", "employee_id")
    def _onchange_leave_params(self):
        if not self.employee_id:
            employee = self.env["hr.employee"].search(
                [("user_id", "=", self.env.uid)], limit=1
            )
            if not employee:
                raise UserError(
                    _(
                        "Your user account is not linked to any employee in this company.\n\n"
                        "Please ask your HR administrator to:\n"
                        "  1. Create or open your employee record.\n"
                        "  2. Set your user account in the 'Related User' field.\n"
                        "  3. Make sure the employee belongs to the correct company."
                    )
                )
            self.employee_id = employee


# =============================================================================
# Refusal Reason Wizard
# =============================================================================
class HrLeaveRefuseReasonWizard(models.TransientModel):
    _name = "hr.leave.refuse.reason.wizard"
    _description = "Leave Refusal Reason"

    leave_ids = fields.Many2many("hr.leave", string="Leave Requests")
    reason = fields.Text(string="Reason for Refusal", required=True)

    def action_confirm_refuse(self):
        self.ensure_one()
        if not self.reason or not self.reason.strip():
            raise UserError(
                _("Please provide a reason for refusing this leave request.")
            )
        self.leave_ids._do_refuse(self.reason.strip())
        return {"type": "ir.actions.act_window_close"}
