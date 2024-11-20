from django.urls import path 
from API import views 

urlpatterns = [
     path('getLinesOfCode/<str:username>', views.getLinesOfCode),
]
