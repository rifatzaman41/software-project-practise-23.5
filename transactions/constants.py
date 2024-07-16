from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives

DEPOSIT = 1
WITHDRAWAL = 2
LOAN = 3
LOAN_PAID = 4
SEND_MONEY = 5
RECEIVE_MONEY = 6
TRANSACTION_TYPE = (
    (DEPOSIT, 'Deposite'),
    (WITHDRAWAL, 'Withdrawal'),
    (LOAN, 'Loan'),
    (LOAN_PAID, 'Loan Paid'),
        (SEND_MONEY, 'Send money'),
    (RECEIVE_MONEY, 'Receive money'),

)

def send_mail_to_user(subject, template_name, context, receiver):
    mail_subject = subject
    sender_mail_message = render_to_string(template_name, context)
    mail = EmailMultiAlternatives(mail_subject, '', to=[receiver])
    mail.attach_alternative(sender_mail_message, 'text/html')
    mail.send()