from django.urls import path 
from API import views 

urlpatterns = [
     path('getExtensions', views.getExtensions),
     path('getLeaderboard', views.getLeaderboard),
     path('refreshAccountData/<str:username>', views.refreshAccountData),
]
