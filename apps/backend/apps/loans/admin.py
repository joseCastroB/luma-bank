from django.contrib import admin

from .models import Loan, LoanInstallment

admin.site.register(Loan)
admin.site.register(LoanInstallment)
