"""Rutas de operaciones bancarias."""

from django.urls import path

from . import views

app_name = "banking"

urlpatterns = [
    path("accounts/", views.AccountsView.as_view(), name="accounts"),
    path("accounts/<str:number>/", views.AccountDetailView.as_view(), name="account-detail"),
    path(
        "accounts/<str:number>/transactions/",
        views.AccountTransactionsView.as_view(),
        name="account-transactions",
    ),
    path("transfers/own/", views.OwnTransferView.as_view(), name="transfer-own"),
    path(
        "transfers/third-party/",
        views.ThirdPartyTransferView.as_view(),
        name="transfer-third-party",
    ),
    path("exchange/quote/", views.ExchangeQuoteView.as_view(), name="exchange-quote"),
    path("exchange/", views.ExchangeView.as_view(), name="exchange"),
    path("transactions/<str:code>/receipt/", views.ReceiptView.as_view(), name="receipt"),
]
