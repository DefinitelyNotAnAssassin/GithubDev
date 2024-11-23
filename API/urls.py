from django.urls import path 
from API import views 

urlpatterns = [
     path('getExtensions', views.getExtensions),
     path('getLeaderboard', views.getLeaderboard),
     path('getLinesOfCode/<str:username>', views.getLinesOfCode),
]
