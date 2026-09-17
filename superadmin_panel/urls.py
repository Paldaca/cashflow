from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='superadmin_dashboard'),
    path('usuarios/', views.usuarios, name='superadmin_usuarios'),
    path('usuarios/guardar/', views.guardar_usuario, name='superadmin_crear_usuario'),
    path('usuarios/guardar/<int:user_id>/', views.guardar_usuario, name='superadmin_editar_usuario'),
    path('usuarios/eliminar/<int:user_id>/', views.eliminar_usuario, name='superadmin_eliminar_usuario'),
    path('organizaciones/', views.organizaciones, name='superadmin_organizaciones'),
    path('organizaciones/crear/', views.crear_organizacion_wizard, name='superadmin_crear_organizacion_wizard'),
    path('organizaciones/guardar/<int:org_id>/', views.guardar_organizacion, name='superadmin_editar_organizacion'),
    path('organizaciones/eliminar/<int:org_id>/', views.eliminar_organizacion, name='superadmin_eliminar_organizacion'),
    path('organizaciones/<int:org_id>/accesos/', views.actualizar_accesos_organizacion, name='superadmin_accesos_organizacion'),
    path('proyectos/', views.proyectos, name='superadmin_proyectos'),
    path('proyectos/<int:project_id>/accesos/', views.actualizar_accesos_proyecto, name='superadmin_accesos_proyecto'),
    path('proyectos/matriz/<int:org_id>/', views.actualizar_matriz_accesos_proyectos, name='superadmin_matriz_accesos_proyectos'),
    path('tasas-bcv/', views.tasas_bcv, name='superadmin_tasas_bcv'),
    path('tasas-bcv/api/', views.tasas_bcv_api, name='superadmin_tasas_bcv_api'),
    path('tasas-bcv/guardar/', views.guardar_tasa_bcv, name='superadmin_guardar_tasa_bcv'),
    path('tasas-bcv/eliminar/<int:rate_id>/', views.eliminar_tasa_bcv, name='superadmin_eliminar_tasa_bcv'),
    path('auditoria/', views.auditoria_transacciones, name='superadmin_auditoria'),
    path('auditoria/<int:log_id>/instantanea/', views.auditoria_snapshot, name='superadmin_auditoria_snapshot'),
]
