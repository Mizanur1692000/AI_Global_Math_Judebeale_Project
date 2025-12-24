from django.urls import path
from . import views

urlpatterns = [
    path('', views.root, name='root'), 
    path('solve/image-with-prompt', views.solve_image_with_prompt, name='solve_image_with_prompt'),
    path('check-solution', views.check_solution, name='check_solution'),
    path('classify', views.classify_message, name='classify'),
    path('generate-question', views.generate_math_question, name='generate_question'),
    
]