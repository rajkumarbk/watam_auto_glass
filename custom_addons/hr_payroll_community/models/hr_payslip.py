from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from pytz import timezone
import babel
from odoo.tools import float_round
import logging

_logger = logging.getLogger(__name__)

# This will generate 16th of days
ROUNDING_FACTOR = 16


class HrPayslip(models.Model):
    """Create new model for getting total Payroll Sheet for an Employee"""
    _name = 'hr.payslip'
    _inherit = 'mail.thread'
    _description = 'Pay Slip'

    struct_id = fields.Many2one(comodel_name='hr.payroll.structure',
                                string='Structure',
                                help='Defines the rules that have to be applied'
                                     ' to this payslip, accordingly '
                                     'to the contract chosen. If you let empty '
                                     'the field contract, this field isn\'t '
                                     'mandatory anymore and thus the rules '
                                     'applied will be all the rules set on the '
                                     'structure of all contracts of the '
                                     'employee valid for the chosen period')
    name = fields.Char(string='Payslip Name', help="Enter Payslip Name")
    number = fields.Char(string='Reference', copy=False,
                         help="References for Payslip", )
    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee',
                                  required=True,
                                  help="Choose Employee for Payslip")
    date_from = fields.Date(string='Date From', required=True,
                            help="Start date for Payslip",
                            default=lambda self: fields.Date.to_string(
                                date.today().replace(day=1)))
    date_to = fields.Date(string='Date To', required=True,
                          help="End date for Payslip",
                          default=lambda self: fields.Date.to_string(
                              (datetime.now() + relativedelta(months=+1, day=1,
                                                              days=-1)).date()))
    # this is chaos: 4 states are defined, 3 are used ('verify' isn't)
    # and 5 exist ('confirm' seems to have existed)
    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('verify', 'Waiting'),
        ('done', 'Done'),
        ('cancel', 'Rejected'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft',
        help="""* When the payslip is created the status is \'Draft\'
                \n* If the payslip is under verification, 
                the status is \'Waiting\'.
                \n* If the payslip is confirmed then status is set to \'Done\'.
                \n* When user cancel payslip the status is \'Rejected\'.""")
    line_ids = fields.One2many('hr.payslip.line',
                               'slip_id',
                               string='Payslip Lines',
                               help="Choose Payslip for line")
    company_id = fields.Many2one('res.company', string='Company',
                                 copy=False, help="Choose Company for line",
                                 default=lambda self: self.env[
                                     'res.company']._company_default_get())
    worked_days_line_ids = fields.One2many('hr.payslip.worked.days',
                                           'payslip_id',
                                           string='Payslip Worked Days',
                                           copy=True,
                                           help="Payslip worked days for line")
    input_line_ids = fields.One2many('hr.payslip.input',
                                     'payslip_id',
                                     string='Payslip Inputs',
                                     help="Choose Payslip Input")
    paid = fields.Boolean(string='Made Payment Order ? ',
                          copy=False, help="Is Payment Order")
    note = fields.Text(string='Internal Note', help="Description for Payslip")
    contract_id = fields.Many2one('hr.contract', string='Contract',
                                  help="Choose Contract for Payslip")
    details_by_salary_rule_category_ids = fields.One2many(
        comodel_name='hr.payslip.line',
        compute='_compute_details_by_salary_rule_category_ids',
        string='Details by Salary Rule Category', help="Details from the salary"
                                                       " rule category")
    credit_note = fields.Boolean(string='Credit Note',
                                 help="Indicates this payslip has "
                                      "a refund of another")
    payslip_run_id = fields.Many2one('hr.payslip.run',
                                     string='Payslip Batches',
                                     copy=False, help="Choose Payslip Run")
    payslip_count = fields.Integer(compute='_compute_payslip_count',
                                   string="Payslip Computation Details",
                                   help="Set Payslip Count")
    
    contract_standard_hours = fields.Float(
        string='Contract Standard Hours', 
        compute='_compute_contract_standard_hours',
        store=True,
        help='Standard working hours based on contract calendar for the period')
    
    actual_working_hours = fields.Float(
        string='Actual Working Hours', 
        compute='_compute_actual_working_hours',
        store=True,
        help='Total hours worked from attendance records')
    
    overtime_hours = fields.Float(
        string='Overtime Hours',
        compute='_compute_overtime_hours',
        store=True,
        help="Total overtime hours from attendance records")

    @api.depends('employee_id', 'date_from', 'date_to')
    def _compute_actual_working_hours(self):
        """从考勤记录计算实际工作小时数"""
        for payslip in self:
            if payslip.employee_id and payslip.date_from and payslip.date_to:
                attendance_records = self.env['hr.attendance'].search([
                    ('employee_id', '=', payslip.employee_id.id),
                    ('check_in', '>=', payslip.date_from),
                    ('check_in', '<=', payslip.date_to),
                    ('check_out', '!=', False)
                ])
                
                total_hours = sum(att.worked_hours for att in attendance_records)
                payslip.actual_working_hours = float_round(total_hours, precision_digits=2)
            else:
                payslip.actual_working_hours = 0.0

    @api.depends('contract_id', 'date_from', 'date_to')
    def _compute_contract_standard_hours(self):
        """从合同日历计算标准工作小时数"""
        for payslip in self:
            if payslip.contract_id and payslip.date_from and payslip.date_to:
                contract = payslip.contract_id
                
                if contract.resource_calendar_id:
                    calendar = contract.resource_calendar_id
                    
                    standard_hours = self._get_standard_hours_from_calendar(
                        calendar, 
                        payslip.date_from, 
                        payslip.date_to
                    )
                    payslip.contract_standard_hours = float_round(standard_hours, precision_digits=2)
                else:
                    company_calendar = contract.company_id.resource_calendar_id
                    if company_calendar:
                        standard_hours = self._get_standard_hours_from_calendar(
                            company_calendar, 
                            payslip.date_from, 
                            payslip.date_to
                        )
                        payslip.contract_standard_hours = float_round(standard_hours, precision_digits=2)
                    else:
                        payslip.contract_standard_hours = self._get_default_standard_hours(
                            payslip.date_from, 
                            payslip.date_to
                        )
            else:
                payslip.contract_standard_hours = 0.0

    @api.depends('employee_id', 'date_from', 'date_to')
    def _compute_overtime_hours(self):
        """基于attendance中的overtime_hours字段计算加班小时数"""
        for payslip in self:
            if payslip.employee_id and payslip.date_from and payslip.date_to:
                attendance_records = self.env['hr.attendance'].search([
                    ('employee_id', '=', payslip.employee_id.id),
                    ('check_in', '>=', payslip.date_from),
                    ('check_in', '<=', payslip.date_to),
                    ('check_out', '!=', False)
                ])
                
                # 直接从attendance记录中获取overtime_hours
                total_overtime = sum(att.overtime_hours for att in attendance_records if att.overtime_hours)
                payslip.overtime_hours = float_round(total_overtime, precision_digits=2)
            else:
                payslip.overtime_hours = 0.0

    def _get_standard_hours_from_calendar(self, calendar, date_from, date_to):
        """从日历获取标准工作小时数"""
        try:
            # 转换日期为datetime对象
            day_from = datetime.combine(fields.Date.from_string(date_from), time.min)
            day_to = datetime.combine(fields.Date.from_string(date_to), time.max)
            
            # 获取时区
            tz = timezone(calendar.tz or self.env.user.tz or 'UTC')
            
            # 计算标准工作小时数（不考虑请假）
            standard_hours = calendar.get_work_hours_count(
                tz.localize(day_from),
                tz.localize(day_to),
                compute_leaves=False,  # 不计算请假
            )
            
            return standard_hours or 0.0
        except Exception as e:
            _logger.error("Error calculating standard hours from calendar: %s", str(e))
            # 出错时返回默认值
            return self._get_default_standard_hours(date_from, date_to)

    def _get_default_standard_hours(self, date_from, date_to):
        """获取默认标准工作小时数（40小时/周）"""
        try:
            # 计算日期范围内的天数
            from_date = fields.Date.from_string(date_from)
            to_date = fields.Date.from_string(date_to)
            
            # 计算工作天数（排除周末）
            total_days = (to_date - from_date).days + 1
            work_days = 0
            
            current_date = from_date
            while current_date <= to_date:
                # 检查是否是工作日（星期一到星期五）
                if current_date.weekday() < 5:  # 0=Monday, 4=Friday
                    work_days += 1
                current_date += relativedelta(days=1)
            
            # 默认每天8小时
            default_hours_per_day = 8.0
            return work_days * default_hours_per_day
        except Exception:
            return 0.0

    def _compute_details_by_salary_rule_category_ids(self):
        """Compute function for Salary Rule Category for getting
         all Categories"""
        for payslip in self:
            payslip.details_by_salary_rule_category_ids = payslip.mapped(
                'line_ids').filtered(lambda line: line.category_id)

    def _compute_payslip_count(self):
        """Compute function for getting Total count of Payslips"""
        for payslip in self:
            payslip.payslip_count = len(payslip.line_ids)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        """Function for adding constrains for payslip datas
        by considering date_from and date_to fields"""
        if any(self.filtered(
                lambda payslip: payslip.date_from > payslip.date_to)):
            raise ValidationError(
                _("Payslip 'Date From' must be earlier 'Date To'."))

    def action_payslip_draft(self):
        """Function for change stage of Payslip"""
        return self.write({'state': 'draft'})

    def action_payslip_done(self):
        """Function for change stage of Payslip"""
        self.action_compute_sheet()
        return self.write({'state': 'done'})

    def action_payslip_cancel(self):
        """Function for change stage of Payslip"""
        return self.write({'state': 'cancel'})

    def action_refund_sheet(self):
        """Function for refund the Payslip sheet"""
        for payslip in self:
            copied_payslip = payslip.copy(
                {'credit_note': True, 'name': _('Refund: ') + payslip.name})
            copied_payslip.action_compute_sheet()
            copied_payslip.action_payslip_done()
        formview_ref = self.env.ref('hr_payroll_community.hr_payslip_view_form',
                                    False)
        treeview_ref = self.env.ref('hr_payroll_community.hr_payslip_view_tree',
                                    False)
        return {
            'name': _("Refund Payslip"),
            'view_mode': 'list, form',
            'view_id': False,
            'res_model': 'hr.payslip',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': "[('id', 'in', %s)]" % copied_payslip.ids,
            'views': [(treeview_ref and treeview_ref.id or False, 'list'),
                      (formview_ref and formview_ref.id or False, 'form')],
            'context': {}
        }

    def unlink(self):
        """Function for unlink the Payslip"""
        if any(self.filtered(
                lambda payslip: payslip.state not in ('draft', 'cancel'))):
            raise UserError(
                _('You cannot delete a payslip which is not draft or cancelled!'
                  ))
        return super(HrPayslip, self).unlink()

    # TODO move this function into hr_contract module, on hr.employee object
    @api.model
    def get_contract(self, employee, date_from, date_to):
        """
        @param employee: recordset of employee
        @param date_from: date_field
        @param date_to: date_field
        @return: returns the ids of all the contracts for the given employee
        that need to be considered for the given dates
        """
        # a contract is valid if it ends between the given dates
        clause_1 = ['&', ('date_end', '<=', date_to),
                    ('date_end', '>=', date_from)]
        # OR if it starts between the given dates
        clause_2 = ['&', ('date_start', '<=', date_to),
                    ('date_start', '>=', date_from)]
        # OR if it starts before the date_from and finish after the
        # date_end (or never finish)
        clause_3 = ['&', ('date_start', '<=', date_from), '|',
                    ('date_end', '=', False), ('date_end', '>=', date_to)]
        clause_final = [('employee_id', '=', employee.id),
                        ('state', '=', 'open'), '|',
                        '|'] + clause_1 + clause_2 + clause_3
        return self.env['hr.contract'].search(clause_final).ids

    def action_compute_sheet(self):
        """Function for compute Payslip sheet"""
        for payslip in self:
            number = payslip.number or self.env['ir.sequence'].next_by_code(
                'salary.slip')
            # delete old payslip lines
            payslip.line_ids.unlink()
            # set the list of contract for which the rules have to be applied
            # if we don't give the contract, then the rules to apply should be
            # for all current contracts of the employee
            contract_ids = payslip.contract_id.ids or \
                           self.get_contract(payslip.employee_id,
                                             payslip.date_from, payslip.date_to)
            lines = [(0, 0, line) for line in
                     self._get_payslip_lines(contract_ids, payslip.id)]
            payslip.write({'line_ids': lines, 'number': number})
        return True

    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):
        """
        @param contracts: Browse record of contracts, date_from, date_to
        @return: returns a list of dict containing the input that should be
        applied for the given contract between date_from and date_to
        """
        res = []
        
        for contract in contracts:
            if contract.payroll_type == 'attendances':
                # ATTENDANCE-BASED CALCULATION
                # Get attendance records for the period
                attendance_records = self.env['hr.attendance'].search([
                    ('employee_id', '=', contract.employee_id.id),
                    ('check_in', '>=', date_from),
                    ('check_in', '<=', date_to),
                    ('check_out', '!=', False)
                ])
                
                # Calculate total worked hours and overtime hours
                total_hours = sum(att.worked_hours for att in attendance_records)
                total_overtime = sum(att.overtime_hours for att in attendance_records if att.overtime_hours)
                
                total_hours = float_round(total_hours, precision_digits=2)
                total_overtime = float_round(total_overtime, precision_digits=2)
                
                # Calculate regular hours (total hours minus overtime)
                regular_hours = total_hours - total_overtime
                
                # Get actual working days
                worked_days = set()
                for attendance in attendance_records:
                    worked_days.add(attendance.check_in.date())
                
                # Add regular hours entry
                res.append({
                    'name': _("Normal Working Hours"),
                    'sequence': 1,
                    'code': 'WORK100',
                    'number_of_days': len(worked_days),
                    'number_of_hours': float_round(regular_hours, precision_digits=2),
                    'contract_id': contract.id,
                })
                
                # Add overtime entry if any
                if total_overtime > 0:
                    res.append({
                        'name': _("Overtime Hours"),
                        'sequence': 2,
                        'code': 'OVERTIME',
                        'number_of_days': len(worked_days),
                        'number_of_hours': float_round(total_overtime, precision_digits=2),
                        'contract_id': contract.id,
                    })
                
            elif contract.payroll_type == 'daily_wage':
                # DAILY WAGE CALCULATION
                # Get attendance records for the period
                attendance_records = self.env['hr.attendance'].search([
                    ('employee_id', '=', contract.employee_id.id),
                    ('check_in', '>=', date_from),
                    ('check_in', '<=', date_to),
                    ('check_out', '!=', False)
                ])
                
                # Get unique worked days
                worked_days = set()
                total_overtime = 0
                for attendance in attendance_records:
                    worked_days.add(attendance.check_in.date())
                    if attendance.overtime_hours:
                        total_overtime += attendance.overtime_hours
                
                total_overtime = float_round(total_overtime, precision_digits=2)
                actual_days = len(worked_days)
                
                # Calculate standard days (based on contract calendar)
                standard_days = self._get_standard_days_for_period(contract, date_from, date_to)
                
                # Determine regular days
                regular_days = min(actual_days, standard_days)
                
                # Calculate overtime days (if any overtime hours)
                overtime_days = total_overtime / 8.0 if total_overtime > 0 else 0  # Assuming 8 hours per day
                
                # Add regular days entry
                res.append({
                    'name': _("Normal Working Days"),
                    'sequence': 1,
                    'code': 'DAILY_WAGE',
                    'number_of_days': float_round(regular_days, precision_digits=2),
                    'number_of_hours': float_round(regular_days * 8, precision_digits=2),  # Assuming 8 hours per day
                    'contract_id': contract.id,
                })
                
                # Add overtime entry if any
                if total_overtime > 0:
                    res.append({
                        'name': _("Overtime Hours"),
                        'sequence': 2,
                        'code': 'OVERTIME',
                        'number_of_days': float_round(overtime_days, precision_digits=2),
                        'number_of_hours': float_round(total_overtime, precision_digits=2),
                        'contract_id': contract.id,
                    })
                
            else:
                # FIXED SALARY CALCULATION (existing logic)
                # fill only if the contract as a working schedule linked
                if contract.resource_calendar_id:
                    day_from = datetime.combine(fields.Date.from_string(date_from),
                                                time.min)
                    day_to = datetime.combine(fields.Date.from_string(date_to),
                                              time.max)
                    # compute leave days
                    leaves = {}
                    calendar = contract.resource_calendar_id
                    tz = timezone(calendar.tz)
                    day_leave_intervals = contract.employee_id.list_leaves(
                        day_from, day_to, calendar=contract.resource_calendar_id)
                    multi_leaves = []
                    for day, hours, leave in day_leave_intervals:
                        work_hours = calendar.get_work_hours_count(
                            tz.localize(datetime.combine(day, time.min)),
                            tz.localize(datetime.combine(day, time.max)),
                            compute_leaves=False,
                        )
                        if len(leave) > 1:
                            for each in leave:
                                if each.holiday_id:
                                    multi_leaves.append(each.holiday_id)
                        else:
                            holiday = leave.holiday_id
                            current_leave_struct = leaves.setdefault(
                                holiday.holiday_status_id, {
                                    'name': holiday.holiday_status_id.name or _(
                                        'Global Leaves'),
                                    'sequence': 5,
                                    'code': holiday.holiday_status_id.code or 'GLOBAL',
                                    'number_of_days': 0.0,
                                    'number_of_hours': 0.0,
                                    'contract_id': contract.id,
                                })
                            current_leave_struct['number_of_hours'] += hours
                            if work_hours:
                                current_leave_struct[
                                    'number_of_days'] += hours / work_hours
                    
                    # compute worked days
                    work_data = contract.employee_id.get_work_days_data(
                        day_from, day_to, calendar=contract.resource_calendar_id)
                    attendances = {
                        'name': _("Normal Working Days paid at 100%"),
                        'sequence': 1,
                        'code': 'WORK100',
                        'number_of_days': work_data['days'],
                        'number_of_hours': work_data['hours'],
                        'contract_id': contract.id,
                    }
                    res.append(attendances)
                    uniq_leaves = [*set(multi_leaves)]
                    c_leaves = {}
                    for rec in uniq_leaves:
                        duration = rec.duration_display.replace("days", "").strip()
                        duration_in_hours = float(duration) * 24
                        c_leaves.setdefault(rec.holiday_status_id,
                                            {'hours': duration_in_hours})
                    for item in c_leaves:
                        if not leaves or item not in leaves:
                            data = {
                                'name': item.name,
                                'sequence': 20,
                                'code': item.code or 'LEAVES',
                                'number_of_hours': c_leaves[item]['hours'],
                                'number_of_days': c_leaves[item][
                                                      'hours'] / work_hours,
                                'contract_id': contract.id,
                            }
                            res.append(data)
                        for time_off in leaves:
                            if item == time_off:
                                leaves[item]['number_of_hours'] += c_leaves[item][
                                    'hours']
                                leaves[item]['number_of_days'] \
                                    += c_leaves[item]['hours'] / work_hours
                    res.extend(leaves.values())
        return res

    def _get_contract_standard_hours_for_period(self, contract, date_from, date_to):
        """Helper method to get standard hours from contract for a period"""
        if contract.resource_calendar_id:
            calendar = contract.resource_calendar_id
        else:
            calendar = contract.company_id.resource_calendar_id
        
        if calendar:
            day_from = datetime.combine(fields.Date.from_string(date_from), time.min)
            day_to = datetime.combine(fields.Date.from_string(date_to), time.max)
            
            # 获取时区
            tz = timezone(calendar.tz or self.env.user.tz or 'UTC')
            
            # 计算标准工作小时数（不考虑请假）
            standard_hours = calendar.get_work_hours_count(
                tz.localize(day_from),
                tz.localize(day_to),
                compute_leaves=False, 
            )
            
            return standard_hours or 0.0
        else:
            return self._get_default_standard_hours(date_from, date_to)

    def _get_standard_days_for_period(self, contract, date_from, date_to):
        """Helper method to get standard working days from contract for a period"""
        if contract.resource_calendar_id:
            calendar = contract.resource_calendar_id
        else:
            calendar = contract.company_id.resource_calendar_id
        
        if calendar:
            # Count working days based on calendar
            working_days = 0
            current_date = fields.Date.from_string(date_from)
            end_date = fields.Date.from_string(date_to)
            
            while current_date <= end_date:
                # Check if this day is a working day according to the calendar
                if calendar.attendance_ids.filtered(lambda a: int(a.dayofweek) == current_date.weekday()):
                    working_days += 1
                current_date += relativedelta(days=1)
            
            return float(working_days)
        else:
            # Default: count weekdays (Monday to Friday)
            start_date = fields.Date.from_string(date_from)
            end_date = fields.Date.from_string(date_to)
            working_days = 0
            current_date = start_date
            
            while current_date <= end_date:
                if current_date.weekday() < 5:  # Monday (0) to Friday (4)
                    working_days += 1
                current_date += relativedelta(days=1)
            
            return float(working_days)

    @api.model
    def get_inputs(self, contracts, date_from, date_to):
        """Function for getting contracts upon date_from and date_to fields"""
        res = []
        structure_ids = contracts.get_all_structures()
        rule_ids = self.env['hr.payroll.structure'].browse(
            structure_ids).get_all_rules()
        sorted_rule_ids = [id for id, sequence in
                           sorted(rule_ids, key=lambda x: x[1])]
        inputs = self.env['hr.salary.rule'].browse(sorted_rule_ids).mapped(
            'input_ids')
        for contract in contracts:
            for input in inputs:
                input_data = {
                    'name': input.name,
                    'code': input.code,
                    'contract_id': contract.id,
                    'date_from': date_from,
                    'date_to': date_to,
                }
                res.append(input_data)
        return res

    @api.model
    def _get_payslip_lines(self, contract_ids, payslip_id):
        """Function for getting Payslip Lines"""

        def _sum_salary_rule_category(localdict, category, amount):
            """Function for getting total sum of Salary Rule Category"""
            if category.parent_id:
                localdict = _sum_salary_rule_category(localdict,
                                                      category.parent_id,
                                                      amount)
            localdict['categories'].dict[category.code] \
                = category.code in localdict[
                'categories'].dict and localdict['categories'].dict[
                      category.code] + amount or amount
            return localdict

        class BrowsableObject(object):
            """Class for Browsable Object"""

            def __init__(self, employee_id, dict, env):
                """Function for getting employee_id,dict and env"""
                self.employee_id = employee_id
                self.dict = dict
                self.env = env

            def __getattr__(self, attr):
                """Function for return dict"""
                return attr in self.dict and self.dict.__getitem__(attr) or 0.0

        class InputLine(BrowsableObject):
            """a class that will be used into the python code, mainly for
            usability purposes"""

            def sum(self, code, from_date, to_date=None):
                """Function for getting sum of Payslip with respect to
                 from_date,to_date fields"""
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""
                    SELECT sum(amount) as sum
                    FROM hr_payslip as hp, hr_payslip_input as pi
                    WHERE hp.employee_id = %s AND hp.state = 'done'
                    AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = 
                    pi.payslip_id AND pi.code = %s""",
                                    (self.employee_id, from_date, to_date,
                                        code))
                return self.env.cr.fetchone()[0] or 0.0

        class WorkedDays(BrowsableObject):
            """a class that will be used into the python code, mainly for
            usability purposes"""

            def _sum(self, code, from_date, to_date=None):
                """Function for getting sum of Payslip days with respect to
                 from_date,to_date fields"""
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""
                    SELECT sum(number_of_days) as number_of_days, 
                    sum(number_of_hours) as number_of_hours
                    FROM hr_payslip as hp, hr_payslip_worked_days as pi
                    WHERE hp.employee_id = %s AND hp.state = 'done'
                    AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = 
                    pi.payslip_id AND pi.code = %s""",
                                    (self.employee_id, from_date, to_date,
                                        code))
                return self.env.cr.fetchone()

            def sum(self, code, from_date, to_date=None):
                """Function for getting sum of Payslip with respect to
                 from_date,to_date fields"""
                res = self._sum(code, from_date, to_date)
                return res and res[0] or 0.0

            def sum_hours(self, code, from_date, to_date=None):
                """Function for getting sum of Payslip hours with respect to
                 from_date,to_date fields"""
                res = self._sum(code, from_date, to_date)
                return res and res[1] or 0.0

        class Payslips(BrowsableObject):
            """a class that will be used into the python code, mainly for
            usability purposes"""

            def sum(self, code, from_date, to_date=None):
                """Function for getting sum of Payslip with respect to
                 from_date,to_date fields"""
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""SELECT sum(case when hp.credit_note = 
                False then (pl.total) else (-pl.total) end)
                FROM hr_payslip as hp, hr_payslip_line as pl
                WHERE hp.employee_id = %s AND hp.state = 'done'
                AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id 
                = pl.slip_id AND pl.code = %s""",
                                    (
                                        self.employee_id, from_date, to_date,
                                        code))
                res = self.env.cr.fetchone()
                return res and res[0] or 0.0

        # we keep a dict with the result because a value can be overwritten
        # by another rule with the same code
        result_dict = {}
        rules_dict = {}
        worked_days_dict = {}
        inputs_dict = {}
        blacklist = []
        payslip = self.env['hr.payslip'].browse(payslip_id)
        for worked_days_line in payslip.worked_days_line_ids:
            worked_days_dict[worked_days_line.code] = worked_days_line
        for input_line in payslip.input_line_ids:
            inputs_dict[input_line.code] = input_line
        
        categories = BrowsableObject(payslip.employee_id.id, {}, self.env)
        inputs = InputLine(payslip.employee_id.id, inputs_dict, self.env)
        worked_days = WorkedDays(payslip.employee_id.id, worked_days_dict,
                                 self.env)
        payslips = Payslips(payslip.employee_id.id, payslip, self.env)
        rules = BrowsableObject(payslip.employee_id.id, rules_dict, self.env)
        
        # FIXED: Make sure all contract fields are available in the context
        baselocaldict = {
            'categories': categories, 
            'rules': rules,
            'payslip': payslips, 
            'worked_days': worked_days,
            'inputs': inputs,
            'contract_standard_hours': payslip.contract_standard_hours,
            'actual_working_hours': payslip.actual_working_hours,
            'overtime_hours': payslip.overtime_hours,
        }
        
        # get the ids of the structures on the contracts and their
        # parent id as well
        contracts = self.env['hr.contract'].browse(contract_ids)
        if len(contracts) == 1 and payslip.struct_id:
            structure_ids = list(
                set(payslip.struct_id._get_parent_structure().ids))
        else:
            structure_ids = contracts.get_all_structures()
        # get the rules of the structure and thier children
        rule_ids = self.env['hr.payroll.structure'].browse(
            structure_ids).get_all_rules()
        # run the rules by sequence
        sorted_rule_ids = [id for id, sequence in
                           sorted(rule_ids, key=lambda x: x[1])]
        sorted_rules = self.env['hr.salary.rule'].browse(sorted_rule_ids)
        
        for contract in contracts:
            employee = contract.employee_id
            # Create localdict with contract specific values - FIX: pass ALL contract fields
            localdict = dict(baselocaldict, employee=employee, contract=contract)
            
            # CRITICAL FIX: Add contract fields directly to localdict
            # This ensures all contract fields are available in salary rule calculations
            for field_name in contract._fields:
                if field_name not in ['id', '__last_update', 'display_name']:
                    try:
                        localdict[field_name] = contract[field_name]
                    except:
                        pass
            
            # DEBUG LOGGING - Add this to see what values are available
            _logger.info("=== OVERTIME CALCULATION DEBUG ===")
            _logger.info("Contract ID: %s", contract.id)
            _logger.info("Employee: %s", employee.name)
            _logger.info("Overtime hours from payslip: %s", payslip.overtime_hours)
            _logger.info("Over hour rate from contract: %s", contract.over_hour)
            _logger.info("Over day rate from contract: %s", contract.over_day)
            _logger.info("Payroll type: %s", contract.payroll_type)
            _logger.info("Calculated overtime amount (hourly): %s", 
                        payslip.overtime_hours * contract.over_hour if contract.over_hour else 0)
            
            for rule in sorted_rules:
                key = rule.code + '-' + str(contract.id)
                localdict['result'] = None
                localdict['result_qty'] = 1.0
                localdict['result_rate'] = 100
                # check if the rule can be applied
                if rule._satisfy_condition(
                        localdict) and rule.id not in blacklist:
                    # compute the amount of the rule
                    amount, qty, rate = rule._compute_rule(localdict)
                    # check if there is already a rule computed with that code
                    previous_amount = rule.code in localdict and localdict[
                        rule.code] or 0.0
                    # set/overwrite the amount computed for this rule in
                    # the localdict
                    tot_rule = amount * qty * rate / 100.0
                    localdict[rule.code] = tot_rule
                    rules_dict[rule.code] = rule
                    # sum the amount for its salary category
                    localdict = _sum_salary_rule_category(
                        localdict, rule.category_id, tot_rule - previous_amount)
                    # create/overwrite the rule in the temporary results
                    result_dict[key] = {
                        'salary_rule_id': rule.id,
                        'contract_id': contract.id,
                        'name': rule.name,
                        'code': rule.code,
                        'category_id': rule.category_id.id,
                        'sequence': rule.sequence,
                        'appears_on_payslip': rule.appears_on_payslip,
                        'condition_select': rule.condition_select,
                        'condition_python': rule.condition_python,
                        'condition_range': rule.condition_range,
                        'condition_range_min': rule.condition_range_min,
                        'condition_range_max': rule.condition_range_max,
                        'amount_select': rule.amount_select,
                        'amount_fix': rule.amount_fix,
                        'amount_python_compute': rule.amount_python_compute,
                        'amount_percentage': rule.amount_percentage,
                        'amount_percentage_base': rule.amount_percentage_base,
                        'register_id': rule.register_id.id,
                        'amount': amount,
                        'employee_id': contract.employee_id.id,
                        'quantity': qty,
                        'rate': rate,
                    }
                else:
                    # blacklist this rule and its children
                    blacklist += [id for id, seq in
                                  rule._recursive_search_of_rules()]
        return list(result_dict.values())

    # YTI
    # TODO To rename. This method is not really an onchange,
    #  as it is not in any view
    # employee_id and contract_id could be browse records
    def onchange_employee_id(self, date_from, date_to, employee_id=False,
                             contract_id=False):
        """Function for return worked days when changing onchange_employee_id"""
        # defaults
        res = {
            'value': {
                'line_ids': [],
                'input_line_ids': [(2, x,) for x in self.input_line_ids.ids],
                'worked_days_line_ids': [(2, x,) for x in
                                         self.worked_days_line_ids.ids],
                'name': '',
                'contract_id': False,
                'struct_id': False,
            }
        }
        if (not employee_id) or (not date_from) or (not date_to):
            return res
        ttyme = datetime.combine(fields.Date.from_string(date_from), time.min)
        employee = self.env['hr.employee'].browse(employee_id)
        locale = self.env.context.get('lang') or 'en_US'
        res['value'].update({
            'name': _('Salary Slip of %s for %s') % (
                employee.name, tools.ustr(
                    babel.dates.format_date(date=ttyme, format='MMMM-y',
                                            locale=locale))),
            'company_id': employee.company_id.id,
        })
        if not self.env.context.get('contract'):
            # fill with the first contract of the employee
            contract_ids = self.get_contract(employee, date_from, date_to)
        else:
            if contract_id:
                # set the list of contract for which the input have to be filled
                contract_ids = [contract_id]
            else:
                # if we don't give the contract, then the input to fill
                # should be for all current contracts of the employee
                contract_ids = self.get_contract(employee, date_from, date_to)
        if not contract_ids:
            return res
        contract = self.env['hr.contract'].browse(contract_ids[0])
        res['value'].update({
            'contract_id': contract.id
        })
        struct = contract.struct_id
        if not struct:
            return res
        res['value'].update({
            'struct_id': struct.id,
        })
        # computation of the salary input
        contracts = self.env['hr.contract'].browse(contract_ids)
        worked_days_line_ids = self.get_worked_day_lines(contracts, date_from,
                                                         date_to)
        input_line_ids = self.get_inputs(contracts, date_from, date_to)
        res['value'].update({
            'worked_days_line_ids': worked_days_line_ids,
            'input_line_ids': input_line_ids,
        })
        return res

    @api.onchange('employee_id', )
    def onchange_employee(self):
        """Function for getting contract for employee"""
        if (not self.employee_id) or (not self.date_from) or (not self.date_to):
            return
        employee = self.employee_id
        date_from = self.date_from
        date_to = self.date_to
        contract_ids = []
        ttyme = datetime.combine(fields.Date.from_string(date_from), time.min)
        locale = self.env.context.get('lang') or 'en_US'
        self.name = _('Salary Slip of %s for %s') % (
            employee.name, tools.ustr(
                babel.dates.format_date(date=ttyme, format='MMMM-y',
                                        locale=locale)))
        self.company_id = employee.company_id
        if not self.env.context.get('contract') or not self.contract_id:
            contract_ids = self.get_contract(employee, date_from, date_to)
            if not contract_ids:
                return
            self.contract_id = self.env['hr.contract'].browse(contract_ids[0])
        if not self.contract_id.struct_id:
            return
        self.struct_id = self.contract_id.struct_id
        if self.contract_id:
            contract_ids = self.contract_id.ids
        # computation of the salary input
        contracts = self.env['hr.contract'].browse(contract_ids)
        worked_days_line_ids = self.get_worked_day_lines(contracts, date_from,
                                                         date_to)
        worked_days_lines = self.worked_days_line_ids.browse([])
        for r in worked_days_line_ids:
            worked_days_lines += worked_days_lines.new(r)
        self.worked_days_line_ids = worked_days_lines
        input_line_ids = self.get_inputs(contracts, date_from, date_to)
        input_lines = self.input_line_ids.browse([])
        for r in input_line_ids:
            input_lines += input_lines.new(r)
        self.input_line_ids = input_lines
        return

    @api.onchange('contract_id')
    def onchange_contract_id(self):
        """Function for getting structure when changing contract"""
        if not self.contract_id:
            self.struct_id = False
        self.with_context(contract=True).onchange_employee()
        return

    def get_salary_line_total(self, code):
        """Function for getting total salary line"""
        self.ensure_one()
        line = self.line_ids.filtered(lambda line: line.code == code)
        if line:
            return line[0].total
        else:
            return 0.0

    @api.onchange('date_from')
    def onchange_date_from(self):
        """Function for getting contract for employee"""
        date_from = self.date_from
        date_to = self.date_to
        contract_ids = []
        if self.contract_id:
            contract_ids = self.contract_id.ids
        # # computation of the salary input
        contracts = self.env['hr.contract'].browse(contract_ids)
        worked_days_line_ids = self.get_worked_day_lines(contracts, date_from,
                                                         date_to)
        worked_days_lines = self.worked_days_line_ids.browse([])
        for r in worked_days_line_ids:
            worked_days_lines += worked_days_lines.new(r)
        self.worked_days_line_ids = worked_days_lines
        input_line_ids = self.get_inputs(contracts, date_from, date_to)
        input_lines = self.input_line_ids.browse([])
        for r in input_line_ids:
            input_lines += input_lines.new(r)
        self.input_line_ids = input_lines
        if self.line_ids.search([('name', '=', 'Meal Voucher')]):
            self.line_ids.search(
                [('name', '=', 'Meal Voucher')]).salary_rule_id.write(
                {'quantity': self.worked_days_line_ids.number_of_days})
        return

    @api.onchange('date_to')
    def onchange_date_to(self):
        """Function for getting contract for employee"""
        if (not self.employee_id) or (not self.date_from) or (not self.date_to):
            return
        date_from = self.date_from
        date_to = self.date_to
        contract_ids = []
        if self.contract_id:
            contract_ids = self.contract_id.ids
        # computation of the salary input
        contracts = self.env['hr.contract'].browse(contract_ids)
        worked_days_line_ids = self.get_worked_day_lines(contracts, date_from,
                                                         date_to)
        worked_days_lines = self.worked_days_line_ids.browse([])
        for r in worked_days_line_ids:
            worked_days_lines += worked_days_lines.new(r)
        self.worked_days_line_ids = worked_days_lines
        input_line_ids = self.get_inputs(contracts, date_from, date_to)
        input_lines = self.input_line_ids.browse([])
        for r in input_line_ids:
            input_lines += input_lines.new(r)
        self.input_line_ids = input_lines
        if self.line_ids.search([('name', '=', 'Meal Voucher')]):
            self.line_ids.search(
                [('name', '=', 'Meal Voucher')]).salary_rule_id.write(
                {'quantity': self.worked_days_line_ids.number_of_days})
        return