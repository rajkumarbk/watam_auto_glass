# -*- coding: utf-8 -*-
#############################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models


class HrContract(models.Model):
    """
    Employee contract based on the visa, work permits
    allows to configure different Salary structure
    """
    _inherit = 'hr.contract'
    _description = 'Employee Contract'

    struct_id = fields.Many2one('hr.payroll.structure',
                                string='Salary Structure',
                                help="Choose Payroll Structure")
    payroll_type = fields.Selection([('fixed', 'Fixed'), ('attendances', 'Attendances'),('daily_wage', 'Daily Wage')], 
                                    string="Payroll Type", default='daily_wage')
    schedule_pay = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi-annually', 'Semi-annually'),
        ('annually', 'Annually'),
        ('weekly', 'Weekly'),
        ('bi-weekly', 'Bi-weekly'),
        ('bi-monthly', 'Bi-monthly'),
    ], string='Scheduled Pay', index=True, default='monthly',
        help="Defines the frequency of the wage payment.")
    hra = fields.Monetary(string='HRA', tracking=True,
                          help="House rent allowance.")
    travel_allowance = fields.Monetary(string="Travel Allowance",
                                       help="Travel allowance")
    da = fields.Monetary(string="DA", help="Dearness allowance")
    meal_allowance = fields.Monetary(string="Meal Allowance",
                                     help="Meal allowance")
    medical_allowance = fields.Monetary(string="Medical Allowance",
                                        help="Medical allowance")
    other_allowance = fields.Monetary(string="Other Allowance",
                                      help="Other allowances")
    # ADDED: Hourly wage field for attendance-based payroll
    hourly_wage = fields.Monetary(string="Hourly Wage", 
                                  help="Hourly wage for attendance-based payroll",
                                  compute='_compute_hourly_wage',
                                  store=True)
    daily_wage = fields.Monetary(string="Daily Wage", 
                                 help="Daily wage for daily wage-based payroll",
                                 compute='_compute_daily_wage',
                                 store=True)
    
    @api.depends('wage', 'hra', 'da', 'travel_allowance', 
                 'meal_allowance', 'medical_allowance', 'other_allowance',
                 'payroll_type', 'resource_calendar_id')
    def _compute_hourly_wage(self):
        """Compute hourly wage based on total monthly compensation / (working_days_per_month * working_hours_per_day)"""
        for contract in self:
            if contract.payroll_type == 'attendances':
                # Calculate total monthly compensation
                total_monthly = contract.wage
                total_monthly += contract.hra or 0
                total_monthly += contract.da or 0
                total_monthly += contract.travel_allowance or 0
                total_monthly += contract.meal_allowance or 0
                total_monthly += contract.medical_allowance or 0
                total_monthly += contract.other_allowance or 0
                
                # Get working days per month
                working_days_per_month = self._get_working_days_per_month(contract)
                # Get working hours per day from calendar
                working_hours_per_day = self._get_working_hours_per_day(contract)
                
                # Calculate hourly wage: monthly total / (working_days_per_month * working_hours_per_day)
                if working_days_per_month > 0 and working_hours_per_day > 0:
                    contract.hourly_wage = total_monthly / (working_days_per_month * working_hours_per_day) if total_monthly else 0.0
                else:
                    contract.hourly_wage = 0.0
            else:
                contract.hourly_wage = 0.0
    
    def _get_working_hours_per_day(self, contract):
        """Get average working hours per day from the calendar"""
        if contract.resource_calendar_id:
            calendar = contract.resource_calendar_id
            # Calculate average hours per day
            total_weekly_hours = 0
            for attendance in calendar.attendance_ids:
                total_weekly_hours += attendance.hour_to - attendance.hour_from
            
            # Get number of working days per week
            working_days_per_week = len(set(attendance.dayofweek for attendance in calendar.attendance_ids))
            
            if working_days_per_week > 0:
                return total_weekly_hours / working_days_per_week
        
        # Default to 8 hours if no calendar or no attendances
        return 8.0
    
    @api.depends('wage', 'hra', 'da', 'travel_allowance', 
                 'meal_allowance', 'medical_allowance', 'other_allowance',
                 'payroll_type')
    def _compute_daily_wage(self):
        """Compute daily wage based on total monthly compensation / 30 days"""
        for contract in self:
            if contract.payroll_type == 'daily_wage':
                # Calculate total monthly compensation
                total_monthly = contract.wage
                total_monthly += contract.hra or 0
                total_monthly += contract.da or 0
                total_monthly += contract.travel_allowance or 0
                total_monthly += contract.meal_allowance or 0
                total_monthly += contract.medical_allowance or 0
                total_monthly += contract.other_allowance or 0
                
                # FIXED: Daily wage = total monthly compensation / 30 days
                # NOT divided by working days per month
                contract.daily_wage = total_monthly / 30.0 if total_monthly else 0.0
            else:
                contract.daily_wage = 0.0
    
    def _get_working_days_per_month(self, contract):
        """Get average working days per month from the calendar"""
        if contract.resource_calendar_id:
            calendar = contract.resource_calendar_id
            # Get number of working days per week
            working_days_per_week = len(set(attendance.dayofweek for attendance in calendar.attendance_ids))
            
            # Calculate average working days per month (approximately 4.33 weeks per month)
            return working_days_per_week * 4.33
        
        # Default to 22 days per month (5 days/week * 4.33 weeks)
        return 22.0

    def get_all_structures(self):
        """
        @return: the structures linked to the given contracts, ordered by
        hierarchy (parent=False first,then first level children and so on)
        and without duplicate
        """
        structures = self.mapped('struct_id')
        if not structures:
            return []
        # YTI TODO return browse records
        return list(set(structures._get_parent_structure().ids))

    def get_attribute(self, code, attribute):
        """Function for return code for Contract"""
        return self.env['hr.contract.advantage.template'].search(
                [('code', '=', code)],
                limit=1)[attribute]

    def set_attribute_value(self, code, active):
        """Function for set code for Contract"""
        for contract in self:
            if active:
                value = self.env['hr.contract.advantage.template'].search(
                    [('code', '=', code)], limit=1).default_value
                contract[code] = value
            else:
                contract[code] = 0.0