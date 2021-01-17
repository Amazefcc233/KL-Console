"""KL_Console URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls import handler400, handler500
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    # path('admin/', admin.site.urls),
    # 网页基础内容 start
    path('',views.index),
    path('404/',views.err404_ne),
    path('500/',views.err500),
    # 网页基础内容 end
    # 用户验证操作 start
    path('login/', views.login),
    path('logout/', views.logout),
    path('mfaVerify/', views.mfaVerify),
    # 用户验证操作 end
    # 综评量化管理操作 start
    path('score/submit/', views.scoreSubmit),
    path('score/verify/', views.scoreVerify),
    # 综评量化管理操作 end
    # api操作 start
    path('api/memberCheck/', views.api_memberCheck),
    path('api/memberInfoLoad/', views.api_memberInfoLoad),
    # api操作 end
]

handler404 = views.err404
handler500 = views.err500