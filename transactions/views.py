from django.shortcuts import render,redirect,get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.http import HttpResponse
from django.views.generic import CreateView, ListView
from transactions.constants import DEPOSIT, WITHDRAWAL,LOAN, LOAN_PAID,SEND_MONEY,RECEIVE_MONEY,send_mail_to_user
from datetime import datetime
from django.db.models import Sum
from transactions.forms import (
    DepositForm,
    WithdrawForm,
    LoanRequestForm,
)
from .models import Transaction
from .forms import TransferForm
from accounts.models import UserBankAccount

class TransactionCreateMixin(LoginRequiredMixin, CreateView):
    template_name = 'transaction_form.html'
    model = Transaction
    title = ''
    success_url = reverse_lazy('transaction_report')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'account': self.request.user.account
        })
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': self.title
        })
        return context

class SendMoneyView(TransactionCreateMixin):
    title = "Send money"
    form_class = TransferForm
    template_name = 'transfer.html'

    def get_initial(self):
        initial = {
            'transaction_type': SEND_MONEY
        }
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data['amount']
        account_no = form.cleaned_data['account_no']

        receiver_account = UserBankAccount.objects.get(account_no=account_no)
        receiver_account.balance += amount
        receiver_account.save(update_fields=['balance'])

        receiver_transaction = Transaction(
            amount=amount, transaction_type=RECEIVE_MONEY, account=receiver_account, balance_after_transaction=receiver_account.balance)
        receiver_transaction.save()

        sender_account = self.request.user.account
        sender_account.balance -= amount
        sender_account.save(update_fields=['balance'])
         
        sender_email = self.request.user.email
        receiver_email = receiver_account.user.email

        send_mail_to_user("Transfer money", 'transaction_sender_email.html', {
            'amount': amount,
            'account_no': account_no,
            'owner': self.request.user
        }, sender_email)

        send_mail_to_user("Transfer money", 'transaction_receiver_email.html', {
            'amount': amount,
            'account_no': sender_account.account_no,
            'owner': receiver_account.user
        }, receiver_email)

        messages.success(self.request, f"{amount} has been sent to Account: {account_no}")
        return super().form_valid(form)

class DepositMoneyView(TransactionCreateMixin):
    form_class = DepositForm
    title = 'Deposit'

    def get_initial(self):
        initial = {'transaction_type': DEPOSIT}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        account = self.request.user.account
        account.balance += amount
        account.save(update_fields=['balance'])

        messages.success(
            self.request,
            f'{"{:,.2f}".format(float(amount))}$ was deposited to your account successfully'
        )
        return super().form_valid(form)

class WithdrawMoneyView(TransactionCreateMixin):
    form_class = WithdrawForm
    title = 'Withdraw Money'

    def get_initial(self):
        initial = {'transaction_type': WITHDRAWAL}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        self.request.user.account.balance -= form.cleaned_data.get('amount')
        self.request.user.account.save(update_fields=['balance'])

        messages.success(
            self.request,
            f'Successfully withdrawn {"{:,.2f}".format(float(amount))}$ from your account'
        )
        return super().form_valid(form)

class LoanRequestView(TransactionCreateMixin):
    form_class = LoanRequestForm
    title = 'Request For Loan'

    def get_initial(self):
        initial = {'transaction_type': LOAN}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        current_loan_count = Transaction.objects.filter(
            account=self.request.user.account, transaction_type=LOAN, loan_approve=True).count()
        if current_loan_count >= 3:
            return HttpResponse("You have crossed the loan limits")
        messages.success(
            self.request,
            f'Loan request for {"{:,.2f}".format(float(amount))}$ submitted successfully'
        )
        return super().form_valid(form)

class TransactionReportView(LoginRequiredMixin, ListView):
    template_name = 'transaction_report.html'
    model = Transaction
    balance = 0

    def get_queryset(self):
        queryset = super().get_queryset().filter(account=self.request.user.account)
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')

        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            queryset = queryset.filter(timestamp__date__gte=start_date, timestamp__date__lte=end_date)
            self.balance = Transaction.objects.filter(
                timestamp__date__gte=start_date, timestamp__date__lte=end_date
            ).aggregate(Sum('amount'))['amount__sum']
        else:
            self.balance = self.request.user.account.balance
        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'account': self.request.user.account
        })
        return context

class PayLoanView(LoginRequiredMixin, View):
    def get(self, request, loan_id):
        loan = get_object_or_404(Transaction, id=loan_id)
        if loan.loan_approve:
            user_account = loan.account
            if loan.amount < user_account.balance:
                user_account.balance -= loan.amount
                loan.balance_after_transaction = user_account.balance
                user_account.save()
                loan.loan_approved = True
                loan.transaction_type = LOAN_PAID
                loan.save()
                return redirect('loan_list')
            else:
                messages.error(
                    self.request,
                    f'Loan amount is greater than available balance'
                )
        return redirect('loan_list')

class LoanListView(LoginRequiredMixin, ListView):
    model = Transaction
    template_name = 'loan_request.html'
    context_object_name = 'loans'

    def get_queryset(self):
        user_account = self.request.user.account
        queryset = Transaction.objects.filter(account=user_account, transaction_type=LOAN)
        return queryset
