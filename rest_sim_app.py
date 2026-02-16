import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
import pymongo
from dotenv import load_dotenv
import os
import hashlib
from datetime import datetime, timedelta
import io

# --- MongoDB Login System (DISABLED) ---
# load_dotenv()
# db_password = os.getenv("db_password")
# mongo_uri = f"mongodb+srv://arsealf_db_user:{db_password}@Cluster001.gkqs2gd.mongodb.net/order_app?retryWrites=true&w=majority&appName=Cluster001"
# client = pymongo.MongoClient(mongo_uri)
# db = client["dash_users"]
# users_collection = db["users"]

# Auto-authenticate for direct access
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = True
if "username" not in st.session_state:
    st.session_state["username"] = "guest"

# def hash_password(password: str) -> str:
#     return hashlib.sha256(password.encode("utf-8")).hexdigest()

# def login(username, password):
#     user = users_collection.find_one({"username": username})
#     if user and user.get("password") == hash_password(password):
#         return True
#     return False

# Login form disabled - direct access enabled
# if not st.session_state["authenticated"]:
#     st.title("🔒 EZ-TEK Restaurant Simulator Login")
#     with st.form("login_form"):
#         username = st.text_input("Usuario")
#         password = st.text_input("Contraseña", type="password")
#         submit = st.form_submit_button("Iniciar sesión")
#     if submit:
#         if login(username, password):
#             st.session_state["authenticated"] = True
#             st.session_state["username"] = username
#             st.success("¡Login exitoso!")
#             st.rerun()
#         else:
#             st.error("Usuario o contraseña incorrectos.")
#     st.stop()

# Initialize session state for scenarios
if 'scenarios' not in st.session_state:
    st.session_state.scenarios = {}
if 'baseline_set' not in st.session_state:
    st.session_state.baseline_set = False

# Configuración de la página
st.set_page_config(
    page_title="SMESA Restaurant Simulator", 
    page_icon="🍽️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
.main-header {
    text-align: center;
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    padding: 2rem;
    border-radius: 10px;
    color: white;
    margin-bottom: 2rem;
}

.metric-card {
    background: #f8f9fa;
    padding: 1rem;
    border-radius: 10px;
    border-left: 4px solid #667eea;
    margin-bottom: 1rem;
}

.best-scenario {
    background: linear-gradient(135deg, #28a745, #20c997);
    color: white;
    padding: 0.5rem;
    border-radius: 5px;
    text-align: center;
    font-weight: bold;
}

.location-card {
    background: #e3f2fd;
    padding: 1rem;
    border-radius: 10px;
    margin: 1rem 0;
}
</style>
""", unsafe_allow_html=True)

# Log off button disabled (login system disabled)
# if st.session_state.get("authenticated", False):
#     with st.sidebar:
#         st.write(f"👤 Usuario: {st.session_state['username']}")
#         if st.button("Cerrar sesión", help="Cerrar la sesión actual"):
#             st.session_state["authenticated"] = False
#             st.session_state["username"] = ""
#             st.rerun()
#         st.divider()

# ==============================================================================
# SIDEBAR CONFIGURATION - MUST COME BEFORE ANY CALCULATIONS
# ==============================================================================

st.sidebar.header("⚙️ Configuración del Restaurante")

# Sección 1: Parámetros Operativos
st.sidebar.subheader("📊 Parámetros Operativos")
ticket_promedio = st.sidebar.number_input(
    "Ticket Promedio (MXN)", 
    min_value=100, 
    max_value=2000, 
    value=700, 
    step=10,
    help="Valor promedio de cada orden"
)

ocupacion_promedio = st.sidebar.slider(
    "Ocupación Promedio (%)", 
    min_value=30, 
    max_value=100, 
    value=70, 
    step=5,
    help="Porcentaje de mesas ocupadas en promedio"
)

rotacion_diaria = st.sidebar.slider(
    "Rotación por Mesa/Día", 
    min_value=1.0, 
    max_value=8.0, 
    value=3.0, 
    step=0.25,
    help="Número de veces que se ocupa cada mesa por día"
)

dias_operacion = st.sidebar.number_input(
    "Días de Operación/Mes", 
    min_value=20, 
    max_value=31, 
    value=30, 
    step=1,
    help="Días que opera el restaurante al mes"
)

# Sección 2: Configuración de Mesas
st.sidebar.subheader("🪑 Mesas por Día de Semana")
mesas_lunes = st.sidebar.number_input("Lunes", min_value=5, max_value=50, value=10, step=1)
mesas_martes = st.sidebar.number_input("Martes", min_value=5, max_value=50, value=10, step=1)
mesas_miercoles = st.sidebar.number_input("Miércoles", min_value=5, max_value=50, value=10, step=1)
mesas_jueves = st.sidebar.number_input("Jueves", min_value=5, max_value=50, value=10, step=1)
mesas_viernes = st.sidebar.number_input("Viernes", min_value=5, max_value=50, value=10, step=1)
mesas_sabado = st.sidebar.number_input("Sábado", min_value=5, max_value=50, value=10, step=1)
mesas_domingo = st.sidebar.number_input("Domingo", min_value=5, max_value=50, value=10, step=1)

# Sección 3: Costos Variables
st.sidebar.subheader("💳 Costos Variables (%)")
comision_bancaria = st.sidebar.slider(
    "Comisión Bancaria (%)", 
    min_value=0.0, 
    max_value=10.0, 
    value=3.0, 
    step=0.1,
    help="Porcentaje de comisión por pagos con tarjeta"
)

fee_plataforma = st.sidebar.slider(
    "Fee EZ-TEK (%)", 
    min_value=0.0, 
    max_value=15.0, 
    value=5.0, 
    step=0.5,
    help="Porcentaje de comisión de la plataforma"
)

costo_ingredientes = st.sidebar.slider(
    "Costo Ingredientes (%)", 
    min_value=10.0, 
    max_value=50.0, 
    value=30.0, 
    step=1.0,
    help="Porcentaje del costo de ingredientes sobre ventas"
)

# Sección 4: Costos Fijos
st.sidebar.subheader("💰 Costos Fijos Mensuales")
personal = st.sidebar.number_input(
    "Personal (MXN)", 
    min_value=0, 
    max_value=200000, 
    value=50000, 
    step=5000,
    help="Salarios y prestaciones del personal"
)

renta = st.sidebar.number_input(
    "Renta y Servicios (MXN)", 
    min_value=0, 
    max_value=100000, 
    value=20000, 
    step=1000,
    help="Renta del local, agua, luz, gas"
)

tecnologia = st.sidebar.number_input(
    "Tecnología (MXN)", 
    min_value=0, 
    max_value=50000, 
    value=5000, 
    step=500,
    help="Software, licencias, mantenimiento de sistemas"
)

marketing = st.sidebar.number_input(
    "Marketing (MXN)", 
    min_value=0, 
    max_value=50000, 
    value=8000, 
    step=500,
    help="Publicidad, promociones, redes sociales"
)

otros_gastos = st.sidebar.number_input(
    "Otros Gastos (MXN)", 
    min_value=0, 
    max_value=50000, 
    value=7000, 
    step=500,
    help="Seguros, permisos, mantenimiento, etc."
)

# Calcular total de costos fijos
total_costos_fijos = personal + renta + tecnologia + marketing + otros_gastos

st.sidebar.metric("Total Costos Fijos", f"${total_costos_fijos:,.0f}")

# Sección 5: Proyecciones
st.sidebar.subheader("🏢 Expansión")
num_ubicaciones = st.sidebar.number_input(
    "Número de Ubicaciones", 
    min_value=1, 
    max_value=50, 
    value=1, 
    step=1,
    help="Número de ubicaciones para proyección"
)

# ==============================================================================
# CORE APP FUNCTIONS
# ==============================================================================

def calculate_monthly_sales_corrected(mesas_por_dia, ocupacion_promedio, rotacion_mesas, ticket_promedio, dias_operacion):
    """
    Calculates monthly sales properly accounting for operating days, tables, and occupancy.
    """
    ocupacion_decimal = ocupacion_promedio / 100 if ocupacion_promedio > 1 else ocupacion_promedio
    
    ventas_diarias = {}
    ordenes_diarias = {}
    
    for dia, mesas in mesas_por_dia.items():
        ordenes_dia = mesas * ocupacion_decimal * rotacion_mesas
        ventas_dia = ordenes_dia * ticket_promedio
        
        ventas_diarias[dia] = ventas_dia
        ordenes_diarias[dia] = ordenes_dia
    
    total_ordenes_semana = sum(ordenes_diarias.values())
    total_ventas_semana = sum(ventas_diarias.values())
    
    semanas_completas = dias_operacion // 7
    dias_adicionales = dias_operacion % 7
    
    if dias_adicionales == 0:
        total_ordenes_mes = total_ordenes_semana * semanas_completas
        ventas_mensuales = total_ventas_semana * semanas_completas
    else:
        dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        ordenes_dias_adicionales = sum(ordenes_diarias[dias_semana[i]] for i in range(dias_adicionales))
        ventas_dias_adicionales = sum(ventas_diarias[dias_semana[i]] for i in range(dias_adicionales))
        
        total_ordenes_mes = (total_ordenes_semana * semanas_completas) + ordenes_dias_adicionales
        ventas_mensuales = (total_ventas_semana * semanas_completas) + ventas_dias_adicionales
    
    return {
        'ventas_mensuales': ventas_mensuales,
        'total_ordenes_mes': total_ordenes_mes,
        'ventas_diarias': ventas_diarias,
        'ordenes_diarias': ordenes_diarias,
        'ocupacion_decimal': ocupacion_decimal,
        'semanas_completas': semanas_completas,
        'dias_adicionales': dias_adicionales
    }

def calcular_metricas_operativas(mesas_por_dia_dict, ocupacion_promedio, rotacion_diaria, ticket_promedio, dias_operacion):
    """Calcula las métricas operativas del restaurante"""
    
    mesas_semana = [mesas_lunes, mesas_martes, mesas_miercoles, mesas_jueves, 
                   mesas_viernes, mesas_sabado, mesas_domingo]
    
    metricas_diarias = []
    for i, dia in enumerate(['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']):
        mesas_dia = mesas_semana[i]
        mesas_ocupadas = mesas_dia * (ocupacion_promedio / 100)
        ordenes_dia = mesas_ocupadas * rotacion_diaria
        ventas_dia = ordenes_dia * ticket_promedio
        
        metricas_diarias.append({
            'dia': dia,
            'mesas_disponibles': mesas_dia,
            'mesas_ocupadas': mesas_ocupadas,
            'ordenes_dia': ordenes_dia,
            'ventas_dia': ventas_dia
        })
    
    total_mesas = sum(mesas_semana)
    ordenes_semanales = sum([m['ordenes_dia'] for m in metricas_diarias])
    ventas_semanales = sum([m['ventas_dia'] for m in metricas_diarias])
    
    # Use corrected calculation
    resultados = calculate_monthly_sales_corrected(
        mesas_por_dia_dict,
        ocupacion_promedio,
        rotacion_diaria,
        ticket_promedio,
        dias_operacion
    )
    
    ordenes_mensuales = resultados['total_ordenes_mes']
    ventas_mensuales = resultados['ventas_mensuales']
    
    return {
        'metricas_diarias': metricas_diarias,
        'total_mesas': total_mesas,
        'ordenes_mensuales': ordenes_mensuales,
        'ventas_mensuales': ventas_mensuales,
        'ordenes_semanales': ordenes_semanales,
        'ventas_semanales': ventas_semanales
    }

def calcular_rentabilidad(ventas_mensuales):
    """Calcula la estructura de rentabilidad"""
    
    ingresos_brutos = ventas_mensuales
    
    costo_comision_bancaria = ingresos_brutos * (comision_bancaria / 100)
    costo_fee_plataforma = ingresos_brutos * (fee_plataforma / 100)
    costo_ingredientes_total = ingresos_brutos * (costo_ingredientes / 100)
    
    total_costos_variables = (costo_comision_bancaria + costo_fee_plataforma + 
                            costo_ingredientes_total)
    
    margen_contribacion = ingresos_brutos - total_costos_variables  # FIXED: Changed from margen_contribacion
    margen_contribacion_pct = (margen_contribacion / ingresos_brutos * 100) if ingresos_brutos > 0 else 0  # FIXED
    
    utilidad_operativa = margen_contribacion - total_costos_fijos  # FIXED
    margen_operativo_pct = (utilidad_operativa / ingresos_brutos * 100) if ingresos_brutos > 0 else 0
    
    return {
        'ingresos_brutos': ingresos_brutos,
        'costo_comision_bancaria': costo_comision_bancaria,
        'costo_fee_plataforma': costo_fee_plataforma,
        'costo_ingredientes': costo_ingredientes_total,
        'total_costos_variables': total_costos_variables,
        'margen_contribucion': margen_contribacion,  # FIXED: Changed from margen_contribacion
        'margen_contribucion_pct': margen_contribacion_pct,  # FIXED
        'utilidad_operativa': utilidad_operativa,
        'margen_operativo_pct': margen_operativo_pct
    }

def proyectar_expansion(metricas_base, rentabilidad_base):
    """Proyecta métricas para diferentes números de ubicaciones"""
    
    proyecciones = []
    
    for ubicaciones in [1, 3, 5, 10, 15]:
        ventas_proyectadas = rentabilidad_base['ingresos_brutos'] * ubicaciones
        rentabilidad_proyectada = calcular_rentabilidad(ventas_proyectadas)
        
        proyecciones.append({
            'ubicaciones': ubicaciones,
            'ventas_mensuales': ventas_proyectadas,
            'utilidad_operativa': rentabilidad_proyectada['utilidad_operativa'],
            'margen_operativo': rentabilidad_proyectada['margen_operativo_pct']
        })
    
    return proyecciones

def calculate_scenario_metrics(scenario_data):
    """Calculate metrics for a given scenario"""
    ticket_promedio_sc = scenario_data.get('ticket_promedio', ticket_promedio)
    ocupacion_promedio_sc = scenario_data.get('ocupacion_promedio', ocupacion_promedio)
    rotacion_diaria_sc = scenario_data.get('rotacion_diaria', rotacion_diaria)
    dias_operacion_sc = scenario_data.get('dias_operacion', dias_operacion)
    
    mesas_semana = scenario_data.get('mesas_semana', [mesas_lunes, mesas_martes, mesas_miercoles, mesas_jueves, mesas_viernes, mesas_sabado, mesas_domingo])
    
    metricas_diarias = []
    for i, dia in enumerate(['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']):
        mesas_dia = mesas_semana[i]
        mesas_ocupadas = mesas_dia * (ocupacion_promedio_sc / 100)
        ordenes_dia = mesas_ocupadas * rotacion_diaria_sc
        ventas_dia = ordenes_dia * ticket_promedio_sc
        
        metricas_diarias.append({
            'dia': dia,
            'mesas_disponibles': mesas_dia,
            'mesas_ocupadas': mesas_ocupadas,
            'ordenes_dia': ordenes_dia,
            'ventas_dia': ventas_dia
        })
    
    resultados = calculate_monthly_sales_corrected(
        dict(zip(['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'], mesas_semana)),
        ocupacion_promedio_sc,
        rotacion_diaria_sc,
        ticket_promedio_sc,
        dias_operacion_sc
    )
    
    ventas_mensuales = resultados['ventas_mensuales']
    total_ordenes_mes = resultados['total_ordenes_mes']
    
    ingresos_brutos = ventas_mensuales
    costo_comision_bancaria = ingresos_brutos * (comision_bancaria / 100)
    costo_fee_plataforma = ingresos_brutos * (fee_plataforma / 100)
    costo_ingredientes_total = ingresos_brutos * (costo_ingredientes / 100)
    total_costos_variables = (costo_comision_bancaria + costo_fee_plataforma + costo_ingredientes_total)
    margen_contribucion = ingresos_brutos - total_costos_variables
    margen_contribucion_pct = (margen_contribucion / ingresos_brutos * 100) if ingresos_brutos > 0 else 0
    utilidad_operativa = margen_contribucion - total_costos_fijos
    margen_operativo_pct = (utilidad_operativa / ingresos_brutos * 100) if ingresos_brutos > 0 else 0
    
    return {
        'ordenes_mensuales': total_ordenes_mes,
        'ventas_mensuales': ventas_mensuales,
        'ingresos_brutos': ingresos_brutos,
        'margen_contribucion': margen_contribucion,
        'margen_contribucion_pct': margen_contribucion_pct,
        'utilidad_operativa': utilidad_operativa,
        'margen_operativo_pct': margen_operativo_pct,
        'costo_comision_bancaria': costo_comision_bancaria,
        'costo_fee_plataforma': costo_fee_plataforma,
        'costo_ingredientes': costo_ingredientes_total,
        'total_costos_variables': total_costos_variables
    }

# ==============================================================================
# NEW FUNCTIONS TO MANAGE AUTOMATIC BASELINE
# ==============================================================================

def create_baseline_from_sidebar():
    """Gathers current sidebar values into a scenario dictionary."""
    return {
        'name': 'Baseline (Actual)',
        'is_baseline': True,
        'auto_generated': True,  # Special flag for auto-baseline
        'ticket_promedio': ticket_promedio,
        'ocupacion_promedio': ocupacion_promedio,
        'rotacion_diaria': rotacion_diaria,
        'dias_operacion': dias_operacion,
        'mesas_semana': [mesas_lunes, mesas_martes, mesas_miercoles, mesas_jueves, 
                       mesas_viernes, mesas_sabado, mesas_domingo],
        'created_at': datetime.now()
    }

def update_auto_baseline():
    """Finds and updates the auto-generated baseline or creates it if it doesn't exist."""
    current_baseline_data = create_baseline_from_sidebar()
    
    # Check if an auto-generated baseline already exists and update it
    for name, data in st.session_state.scenarios.items():
        if data.get('auto_generated', False):
            st.session_state.scenarios[name] = current_baseline_data
            return # Exit after updating

    # If no auto-generated baseline was found, add it.
    # This ensures it's always present.
    st.session_state.scenarios['Baseline (Actual)'] = current_baseline_data
    st.session_state.baseline_set = True # Mark that a baseline is now available

# ==============================================================================
# NOW CALCULATE METRICS - AFTER ALL VARIABLES ARE DEFINED
# ==============================================================================

# Create mesas dictionary for the corrected calculation
mesas_por_dia_dict = {
    'Lunes': mesas_lunes,
    'Martes': mesas_martes,
    'Miércoles': mesas_miercoles,
    'Jueves': mesas_jueves,
    'Viernes': mesas_viernes,
    'Sábado': mesas_sabado,
    'Domingo': mesas_domingo
}

# Calculate metrics
metricas = calcular_metricas_operativas(
    mesas_por_dia_dict,
    ocupacion_promedio,
    rotacion_diaria,
    ticket_promedio,
    dias_operacion
)
rentabilidad = calcular_rentabilidad(metricas['ventas_mensuales'])
proyecciones = proyectar_expansion(metricas, rentabilidad)

# --- NEW: Call the function to update the baseline on every run ---
update_auto_baseline()

# ==============================================================================
# DASHBOARD PRINCIPAL
# ==============================================================================

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📊 Métricas Operativas del Restaurante")
    
    met1, met2, met3, met4 = st.columns(4)
    with met1:
        st.metric("Ventas Mensuales", f"${metricas['ventas_mensuales']:,.0f}")
    with met2:
        st.metric("Órdenes/Mes", f"{metricas['ordenes_mensuales']:,.0f}")
    with met3:
        st.metric("Ticket Promedio", f"${ticket_promedio}")
    with met4:
        st.metric("Total Mesas", f"{metricas['total_mesas']}")

with col2:
    st.subheader("💰 Análisis de Rentabilidad")
    
    rent1, rent2 = st.columns(2)
    with rent1:
        st.metric(
            "Contribución Marginal", 
            f"${rentabilidad['margen_contribucion']:,.0f}",
            f"{rentabilidad['margen_contribucion_pct']:.1f}%"
        )
    with rent2:
        st.metric(
            "Utilidad Operativa", 
            f"${rentabilidad['utilidad_operativa']:,.0f}",
            f"{rentabilidad['margen_operativo_pct']:.1f}%"
        )

st.divider()

# Gráficos de análisis
tab1, tab2, tab4 = st.tabs([
    "📅 Análisis Semanal", 
    "💹 Estructura P&L", 
    "📈 Sensibilidad"
])

with tab1:
    st.subheader("📅 Distribución Semanal de Ventas")
    
    df_semanal = pd.DataFrame(metricas['metricas_diarias'])
    
    fig1 = go.Figure()
    fig1.add_trace(go.Bar(
        x=df_semanal['dia'],
        y=df_semanal['ventas_dia'],
        marker_color='#4ECDC4',
        text=[f"${x:,.0f}" for x in df_semanal['ventas_dia']],
        textposition='auto',
        name='Ventas Diarias'
    ))
    
    fig1.update_layout(
        title="Ventas Diarias por Día de la Semana",
        xaxis_title="Día",
        yaxis_title="Ventas (MXN)",
        height=400
    )
    
    st.plotly_chart(fig1, use_container_width=True)
    
    st.subheader("📋 Detalle por Día de la Semana")
    df_display = df_semanal.copy()
    df_display['ventas_dia_fmt'] = df_display['ventas_dia'].apply(lambda x: f"${x:,.0f}")
    df_display['ordenes_dia_fmt'] = df_display['ordenes_dia'].apply(lambda x: f"{x:.0f}")
    df_display['mesas_ocupadas_fmt'] = df_display['mesas_ocupadas'].apply(lambda x: f"{x:.1f}")
    
    st.dataframe(
        df_display[['dia', 'mesas_disponibles', 'mesas_ocupadas_fmt', 'ordenes_dia_fmt', 'ventas_dia_fmt']],
        hide_index=True,
        use_container_width=True
    )

with tab2:
    st.subheader("💹 Estado de Resultados (P&L)")
    
    fig2 = go.Figure(go.Waterfall(
        name = "P&L",
        orientation = "v",
        measure = ["relative", "relative", "relative", "relative", "relative", "total"],
        x = ["Ingresos Brutos", "Comisión Bancaria", "Fee EZ-TEK", "Costo Ingredientes", "Costos Fijos", "Utilidad Neta"],
        textposition = "outside",
        text = [f"${rentabilidad['ingresos_brutos']:,.0f}", 
                f"-${rentabilidad['costo_comision_bancaria']:,.0f}",
                f"-${rentabilidad['costo_fee_plataforma']:,.0f}",
                f"-${rentabilidad['costo_ingredientes']:,.0f}",
                f"-${total_costos_fijos:,.0f}",
                f"${rentabilidad['utilidad_operativa']:,.0f}"],
        y = [rentabilidad['ingresos_brutos'], 
             -rentabilidad['costo_comision_bancaria'],
             -rentabilidad['costo_fee_plataforma'],
             -rentabilidad['costo_ingredientes'],
             -total_costos_fijos,
             rentabilidad['utilidad_operativa']],
        connector = {"line":{"color":"rgb(63, 63, 63)"}},
    ))
    
    fig2.update_layout(
        title = "Análisis Cascada de P&L Mensual",
        showlegend = False,
        height=500
    )
    
    st.plotly_chart(fig2, use_container_width=True)
    
    st.subheader("📊 Resumen P&L")
    pl_data = {
        'Concepto': [
            'Ingresos Brutos',
            'Comisión Bancaria',
            'Fee SMESA', 
            'Costo Ingredientes',
            'Total Costos Variables',
            'Contribución Marginal',
            'Costos Fijos',
            'Utilidad Operativa'
        ],
        'Monto': [
            f"${rentabilidad['ingresos_brutos']:,.0f}",
            f"-${rentabilidad['costo_comision_bancaria']:,.0f}",
            f"-${rentabilidad['costo_fee_plataforma']:,.0f}",
            f"-${rentabilidad['costo_ingredientes']:,.0f}",
            f"-${rentabilidad['total_costos_variables']:,.0f}",
            f"${rentabilidad['margen_contribucion']:,.0f}",
            f"-${total_costos_fijos:,.0f}",
            f"${rentabilidad['utilidad_operativa']:,.0f}"
        ],
        'Porcentaje': [
            "100.0%",
            f"{comision_bancaria:.1f}%",
            f"{fee_plataforma:.1f}%",
            f"{costo_ingredientes:.1f}%",
            f"{rentabilidad['total_costos_variables']/rentabilidad['ingresos_brutos']*100:.1f}%",
            f"{rentabilidad['margen_contribucion_pct']:.1f}%",
            f"{total_costos_fijos/rentabilidad['ingresos_brutos']*100:.1f}%",
            f"{rentabilidad['margen_operativo_pct']:.1f}%"
        ]
    }
    
    df_pl = pd.DataFrame(pl_data)
    st.dataframe(df_pl, hide_index=True, use_container_width=True)

# HIDDEN: Proyección Expansión tab
# with tab3:
#     st.subheader("🚀 Proyección de Expansión Geográfica")
#     
#     df_proyecciones = pd.DataFrame(proyecciones)
#     
#     fig3 = make_subplots(specs=[[{"secondary_y": True}]])
#     
#     fig3.add_trace(
#         go.Bar(
#             x=df_proyecciones['ubicaciones'],
#             y=df_proyecciones['ventas_mensuales'],
#             name="Ventas Mensuales",
#             marker_color='#4ECDC4'
#         ),
#         secondary_y=False,
#     )
#     
#     fig3.add_trace(
#         go.Scatter(
#             x=df_proyecciones['ubicaciones'],
#             y=df_proyecciones['margen_operativo'],
#             mode='lines+markers',
#             name="Margen Operativo %",
#             line=dict(color='#FF6B6B', width=3),
#             marker=dict(size=8)
#         ),
#         secondary_y=True,
#     )
#     
#     fig3.update_xaxes(title_text="Número de Ubicaciones")
#     fig3.update_yaxes(title_text="Ventas Mensuales (MXN)", secondary_y=False)
#     fig3.update_yaxes(title_text="Margen Operativo (%)", secondary_y=True)
#     fig3.update_layout(title_text="Escalabilidad del Negocio", height=400)
#     
#     st.plotly_chart(fig3, use_container_width=True)
#     
#     st.subheader("📈 Tabla de Proyecciones")
#     df_proy_display = df_proyecciones.copy()
#     df_proy_display['ventas_mensuales_fmt'] = df_proy_display['ventas_mensuales'].apply(lambda x: f"${x:,.0f}")
#     df_proy_display['utilidad_operativa_fmt'] = df_proy_display['utilidad_operativa'].apply(lambda x: f"${x:,.0f}")
#     df_proy_display['margen_operativo_fmt'] = df_proy_display['margen_operativo'].apply(lambda x: f"{x:.1f}%")
#     
#     st.dataframe(
#         df_proy_display[['ubicaciones', 'ventas_mensuales_fmt', 'utilidad_operativa_fmt', 'margen_operativo_fmt']],
#         hide_index=True,
#         use_container_width=True
#     )

with tab4:
    st.subheader("📈 Análisis de Sensibilidad")
    
    # Change from ticket range to orders range - Extended to touch X-axis
    ordenes_range = np.arange(0, 3500, 100)  # Range of monthly orders to test (extended from 0 to 3500)
    sensibilidad_data = []
    
    for ordenes_test in ordenes_range:
        ventas_test = ordenes_test * ticket_promedio  # Keep current ticket, vary orders
        rent_test = calcular_rentabilidad(ventas_test)
        sensibilidad_data.append({
            'ordenes': ordenes_test,
            'utilidad': rent_test['utilidad_operativa'],
            'margen': rent_test['margen_operativo_pct'],
            'ventas': ventas_test
        })
    
    df_sens = pd.DataFrame(sensibilidad_data)
    
    # Create the graph showing orders vs profit
    fig4 = go.Figure()
    fig4.add_trace(go.Scatter(
        x=df_sens['ordenes'],
        y=df_sens['utilidad'],
        mode='lines+markers',
        name='Utilidad Operativa',
        line=dict(color='#45B7D1', width=3),
        marker=dict(size=6)
    ))
    
    # Add current orders vertical line
    fig4.add_vline(
        x=metricas['ordenes_mensuales'], 
        line_dash="dash", 
        line_color="green",
        annotation_text=f"Actual: {metricas['ordenes_mensuales']:,.0f} órdenes"
    )
    
    # Calculate and add break-even line
    break_even_orders = total_costos_fijos / (ticket_promedio * (1 - (comision_bancaria + fee_plataforma + costo_ingredientes)/100))
    
    fig4.add_vline(
        x=break_even_orders,
        line_dash="dot",
        line_color="red",
        annotation_text=f"Punto Equilibrio: {break_even_orders:,.0f} órdenes"
    )
    
    # Add horizontal line at zero profit
    fig4.add_hline(
        y=0,
        line_dash="solid",
        line_color="gray",
        opacity=0.5
    )
    
    fig4.update_layout(
        title="Sensibilidad: Utilidad vs Número de Órdenes Mensuales",
        xaxis_title="Número de Órdenes Mensuales",
        yaxis_title="Utilidad Operativa (MXN)",
        height=400
    )
    
    st.plotly_chart(fig4, use_container_width=True)
    
    # Enhanced break-even analysis
    col_sens1, col_sens2 = st.columns(2)
    
    with col_sens1:
        st.info(f"🎯 **Punto de Equilibrio**: {break_even_orders:,.0f} órdenes mensuales para cubrir costos fijos")
        
        # Calculate how many more/fewer orders needed
        orders_difference = metricas['ordenes_mensuales'] - break_even_orders
        if orders_difference > 0:
            st.success(f"✅ **Superávit**: {orders_difference:,.0f} órdenes por encima del punto de equilibrio")
        else:
            st.error(f"⚠️ **Déficit**: {abs(orders_difference):,.0f} órdenes adicionales necesarias para equilibrio")
    
    with col_sens2:
        st.info(f"💰 **Contribución por Orden**: ${ticket_promedio * (1 - (comision_bancaria + fee_plataforma + costo_ingredientes)/100):,.2f}")
        
        # Calculate daily orders needed for break-even
        daily_break_even = break_even_orders / dias_operacion
        st.info(f"📅 **Órdenes Diarias Necesarias**: {daily_break_even:.1f} órdenes/día para equilibrio")
    
    # Sensitivity table
    st.subheader("📊 Tabla de Sensibilidad")
    
    # Create summary table with key sensitivity points
    sensitivity_points = [
        int(break_even_orders * 0.8),  # 80% of break-even
        int(break_even_orders),        # Break-even point
        int(metricas['ordenes_mensuales']),  # Current
        int(break_even_orders * 1.2),  # 120% of break-even
        int(break_even_orders * 1.5)   # 150% of break-even
    ]
    
    sensitivity_summary = []
    for orders in sensitivity_points:
        ventas = orders * ticket_promedio
        rent = calcular_rentabilidad(ventas)
        
        # Determine the scenario type
        if orders < break_even_orders:
            scenario_type = "Por debajo del equilibrio"
        elif orders == break_even_orders:
            scenario_type = "Punto de equilibrio"
        elif orders == int(metricas['ordenes_mensuales']):
            scenario_type = "Situación actual"
        else:
            scenario_type = "Por encima del equilibrio"
        
        sensitivity_summary.append({
            'Escenario': scenario_type,
            'Órdenes Mensuales': f"{orders:,}",
            'Ventas Mensuales': f"${ventas:,.0f}",
            'Utilidad Operativa': f"${rent['utilidad_operativa']:,.0f}",
            'Margen Operativo': f"{rent['margen_operativo_pct']:.1f}%"
        })
    
    df_sensitivity = pd.DataFrame(sensitivity_summary)
    st.dataframe(df_sensitivity, hide_index=True, use_container_width=True)
    
    # Additional insights
    st.subheader("💡 Insights del Análisis de Sensibilidad")
    
    insight_col1, insight_col2 = st.columns(2)
    
    with insight_col1:
        # Calculate orders needed for target profit margins
        target_margins = [5, 10, 15, 20]  # Target profit margins in %
        st.markdown("**Órdenes para Márgenes Objetivo:**")
        
        for margin in target_margins:
            target_profit = total_costos_fijos / (1 - margin/100)
            target_orders_needed = target_profit / (ticket_promedio * (1 - (comision_bancaria + fee_plataforma + costo_ingredientes)/100))
            st.write(f"• {margin}% margen: {target_orders_needed:,.0f} órdenes")
    
    with insight_col2:
        # Calculate revenue impact of order changes
        st.markdown("**Impacto de Cambios en Órdenes:**")
        
        order_changes = [100, 200, 500, 1000]  # Additional orders
        for change in order_changes:
            additional_revenue = change * ticket_promedio
            additional_profit = change * (ticket_promedio * (1 - (comision_bancaria + fee_plataforma + costo_ingredientes)/100))
            st.write(f"• +{change} órdenes: +${additional_profit:,.0f} utilidad")

st.divider()

# ==============================================================================
# SCENARIO COMPARISON SECTION - MODIFIED FOR AUTO-BASELINE
# ==============================================================================

st.header("📊 Comparación de Escenarios")

# --- MODIFIED: Display the current auto-baseline configuration ---
st.subheader("📋 Configuración Base (Desde la Barra Lateral)")
auto_baseline_config = create_baseline_from_sidebar()
auto_baseline_metrics = calculate_scenario_metrics(auto_baseline_config)

col_base1, col_base2, col_base3 = st.columns(3)
with col_base1:
    st.metric("Ventas Mensuales (Base)", f"${auto_baseline_metrics['ventas_mensuales']:,.0f}")
with col_base2:
    st.metric("Utilidad Operativa (Base)", f"${auto_baseline_metrics['utilidad_operativa']:,.0f}")
with col_base3:
    st.metric("Margen Operativo (Base)", f"{auto_baseline_metrics['margen_operativo_pct']:.1f}%")
st.info("La configuración de la barra lateral se usa automáticamente como el 'Baseline' para todas las comparaciones.")


col1, col2 = st.columns([3, 1])

with col1:
    st.subheader("Crear Escenarios Alternativos")
    st.write("Define variaciones de la configuración actual para comparar el impacto en la rentabilidad.")

with col2:
    if st.button("🔄 Reiniciar Escenarios", type="secondary"):
        # --- MODIFIED: Keep the auto-baseline when resetting ---
        auto_baseline_item = {k: v for k, v in st.session_state.scenarios.items() if v.get('auto_generated')}
        st.session_state.scenarios = auto_baseline_item
        st.session_state.baseline_set = bool(auto_baseline_item)
        st.rerun()

st.divider()

# --- MODIFIED: The form now only creates alternative scenarios ---
scenario_input_col1, scenario_input_col2 = st.columns(2)

with scenario_input_col1:
    st.subheader("📝 Definir Escenario Alternativo")
    
    scenario_name = st.text_input(
        "Nombre del Escenario", 
        value=f"Escenario {len([s for s in st.session_state.scenarios if not st.session_state.scenarios[s].get('auto_generated')]) + 1}",
        help="Dale un nombre descriptivo a tu escenario alternativo"
    )
    
    # REMOVED the 'is_baseline' checkbox as it's now automatic
    
    col_a, col_b = st.columns(2)
    with col_a:
        ticket_sc = st.number_input("Ticket Promedio (MXN)", min_value=100, max_value=2000, value=ticket_promedio, step=10, key="sc_ticket")
        ocupacion_sc = st.slider("Ocupación Promedio (%)", min_value=30, max_value=100, value=ocupacion_promedio, step=5, key="sc_ocupacion")
    
    with col_b:
        rotacion_sc = st.slider("Rotación por Mesa/Día", min_value=1.0, max_value=8.0, value=rotacion_diaria, step=0.25, key="sc_rotacion")
        dias_sc = st.number_input("Días de Operación/Mes", min_value=20, max_value=31, value=dias_operacion, step=1, key="sc_dias")

with scenario_input_col2:
    st.subheader("🪑 Configuración de Mesas")
    
    st.write("Mesas disponibles por día de la semana:")
    col_sc1, col_sc2 = st.columns(2)
    with col_sc1:
        mesas_lunes_sc = st.number_input("Lun", min_value=5, max_value=50, value=mesas_lunes, step=1, key="sc_lunes")
        mesas_martes_sc = st.number_input("Mar", min_value=5, max_value=50, value=mesas_martes, step=1, key="sc_martes")
        mesas_miercoles_sc = st.number_input("Mié", min_value=5, max_value=50, value=mesas_miercoles, step=1, key="sc_miercoles")
        mesas_jueves_sc = st.number_input("Jue", min_value=5, max_value=50, value=mesas_jueves, step=1, key="sc_jueves")
    with col_sc2:
        mesas_viernes_sc = st.number_input("Vie", min_value=5, max_value=50, value=mesas_viernes, step=1, key="sc_viernes")
        mesas_sabado_sc = st.number_input("Sáb", min_value=5, max_value=50, value=mesas_sabado, step=1, key="sc_sabado")
        mesas_domingo_sc = st.number_input("Dom", min_value=5, max_value=50, value=mesas_domingo, step=1, key="sc_domingo")

# Add scenario button
if st.button("➕ Agregar Escenario a Tabla Comparativa", type="primary", use_container_width=True):
    if scenario_name in st.session_state.scenarios:
        st.error(f"El escenario '{scenario_name}' ya existe. Por favor usa un nombre diferente.")
    else:
        scenario_data = {
            'name': scenario_name,
            'is_baseline': False, # User-created scenarios are never the baseline
            'ticket_promedio': ticket_sc,
            'ocupacion_promedio': ocupacion_sc,
            'rotacion_diaria': rotacion_sc,
            'dias_operacion': dias_sc,
            'mesas_semana': [mesas_lunes_sc, mesas_martes_sc, mesas_miercoles_sc, mesas_jueves_sc, 
                           mesas_viernes_sc, mesas_sabado_sc, mesas_domingo_sc],
            'created_at': datetime.now()
        }
        
        st.session_state.scenarios[scenario_name] = scenario_data
        
        # This is no longer needed as the auto-baseline handles it
        # if is_baseline:
        #     st.session_state.baseline_set = True
        
        st.success(f"✅ Escenario '{scenario_name}' agregado exitosamente!")
        st.rerun()

# Display scenarios and calculations
if st.session_state.scenarios:
    st.divider()
    st.header("📈 Análisis y Comparación de Escenarios")
    
    # Find baseline scenario
    baseline = None
    baseline_name = None
    # --- MODIFIED: Prioritize the auto-generated baseline ---
    for scenario_name, scenario_data in st.session_state.scenarios.items():
        if scenario_data.get('auto_generated', False):
            baseline = scenario_data
            baseline_name = scenario_name
            break # Found the auto-baseline, no need to look further
    
    # Fallback to a user-defined one if auto is somehow missing
    if baseline is None:
        for scenario_name, scenario_data in st.session_state.scenarios.items():
            if scenario_data.get('is_baseline', False):
                baseline = scenario_data
                baseline_name = scenario_name
                break

    if baseline is None:
        st.warning("⚠️ No se encontró un escenario base. La comparación de mejoras está deshabilitada.")
    
    # Calculate metrics for all scenarios
    scenarios_df = []
    
    for scenario_name, scenario in st.session_state.scenarios.items():
        # Calculate scenario metrics
        metrics = calculate_scenario_metrics(scenario)
        
        # Calculate total tables for this scenario
        total_tables = sum(scenario['mesas_semana'])
        
        # Calculate performance improvements vs baseline
        improvements = {
            'ticket_increase': 0,
            'occupancy_increase': 0,
            'turnover_increase': 0,
            'tables_added': 0,
            'revenue_increase': 0
        }
        
        additional_revenue = {
            'from_ticket': 0,
            'from_occupancy': 0,
            'from_turnover': 0,
            'from_tables': 0
        }
        
        if baseline and scenario_name != baseline_name:
            baseline_metrics = calculate_scenario_metrics(baseline)
            baseline_total_tables = sum(baseline['mesas_semana'])
            
            # Calculate improvements
            improvements['ticket_increase'] = ((scenario['ticket_promedio'] - baseline['ticket_promedio']) / baseline['ticket_promedio'] * 100) if baseline['ticket_promedio'] > 0 else 0
            improvements['occupancy_increase'] = scenario['ocupacion_promedio'] - baseline['ocupacion_promedio']
            improvements['turnover_increase'] = ((scenario['rotacion_diaria'] - baseline['rotacion_diaria']) / baseline['rotacion_diaria'] * 100) if baseline['rotacion_diaria'] > 0 else 0
            improvements['tables_added'] = total_tables - baseline_total_tables
            improvements['revenue_increase'] = ((metrics['ventas_mensuales'] - baseline_metrics['ventas_mensuales']) / baseline_metrics['ventas_mensuales'] * 100) if baseline_metrics['ventas_mensuales'] > 0 else 0
            
            # Calculate additional revenue from each improvement type using proper monthly calculation
            # Revenue from ticket increase (using proper monthly calculation)
            if improvements['ticket_increase'] != 0:
                # Create a hypothetical scenario with only ticket changed
                baseline_mesas_dict = dict(zip(['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'], baseline['mesas_semana']))
                
                # Calculate baseline revenue
                baseline_results = calculate_monthly_sales_corrected(
                    baseline_mesas_dict, baseline['ocupacion_promedio'], baseline['rotacion_diaria'], baseline['ticket_promedio'], baseline['dias_operacion']
                )
                
                # Calculate revenue with improved ticket
                improved_ticket_results = calculate_monthly_sales_corrected(
                    baseline_mesas_dict, baseline['ocupacion_promedio'], baseline['rotacion_diaria'], scenario['ticket_promedio'], baseline['dias_operacion']
                )
                
                additional_revenue['from_ticket'] = improved_ticket_results['ventas_mensuales'] - baseline_results['ventas_mensuales']
            
            # Revenue from occupancy increase (using proper monthly calculation)
            if improvements['occupancy_increase'] != 0:
                # Create a hypothetical scenario with only occupancy changed
                baseline_mesas_dict = dict(zip(['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'], baseline['mesas_semana']))
                
                # Calculate baseline revenue
                baseline_results = calculate_monthly_sales_corrected(
                    baseline_mesas_dict, baseline['ocupacion_promedio'], baseline['rotacion_diaria'], baseline['ticket_promedio'], baseline['dias_operacion']
                )
                
                # Calculate revenue with improved occupancy
                improved_occupancy_results = calculate_monthly_sales_corrected(
                    baseline_mesas_dict, scenario['ocupacion_promedio'], baseline['rotacion_diaria'], baseline['ticket_promedio'], baseline['dias_operacion']
                )
                
                additional_revenue['from_occupancy'] = improved_occupancy_results['ventas_mensuales'] - baseline_results['ventas_mensuales']
            
            # Revenue from turnover increase (using proper monthly calculation)
            if improvements['turnover_increase'] != 0:
                # Create a hypothetical scenario with only turnover changed
                baseline_mesas_dict = dict(zip(['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'], baseline['mesas_semana']))
                
                # Calculate baseline revenue
                baseline_results = calculate_monthly_sales_corrected(
                    baseline_mesas_dict, baseline['ocupacion_promedio'], baseline['rotacion_diaria'], baseline['ticket_promedio'], baseline['dias_operacion']
                )
                
                # Calculate revenue with improved turnover
                improved_turnover_results = calculate_monthly_sales_corrected(
                    baseline_mesas_dict, baseline['ocupacion_promedio'], scenario['rotacion_diaria'], baseline['ticket_promedio'], baseline['dias_operacion']
                )
                
                additional_revenue['from_turnover'] = improved_turnover_results['ventas_mensuales'] - baseline_results['ventas_mensuales']
            
            # Revenue from tables change (using proper monthly calculation)
            if improvements['tables_added'] != 0:
                # Calculate revenue with baseline tables vs scenario tables (keeping other factors the same)
                baseline_mesas_dict = dict(zip(['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'], baseline['mesas_semana']))
                scenario_mesas_dict = dict(zip(['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'], scenario['mesas_semana']))
                
                # Calculate baseline revenue with baseline parameters except tables
                baseline_results = calculate_monthly_sales_corrected(
                    baseline_mesas_dict, baseline['ocupacion_promedio'], baseline['rotacion_diaria'], baseline['ticket_promedio'], baseline['dias_operacion']
                )
                
                # Calculate revenue with scenario tables but baseline other parameters
                scenario_tables_results = calculate_monthly_sales_corrected(
                    scenario_mesas_dict, baseline['ocupacion_promedio'], baseline['rotacion_diaria'], baseline['ticket_promedio'], baseline['dias_operacion']
                )
                
                additional_revenue['from_tables'] = scenario_tables_results['ventas_mensuales'] - baseline_results['ventas_mensuales']
        
        scenarios_df.append({
            'scenario_name': scenario_name,
            'is_baseline': scenario.get('is_baseline', False),
            'total_tables': total_tables,
            'ticket_promedio': scenario['ticket_promedio'],
            'ocupacion_promedio': scenario['ocupacion_promedio'],
            'rotacion_diaria': scenario['rotacion_diaria'],
            'dias_operacion': scenario['dias_operacion'],
            'ordenes_mensuales': metrics['ordenes_mensuales'],
            'ventas_mensuales': metrics['ventas_mensuales'],
            'margen_contribucion': metrics['margen_contribucion'],
            'utilidad_operativa': metrics['utilidad_operativa'],
            'margen_operativo': metrics['margen_operativo_pct'],
            'improvements': improvements,
            'additional_revenue': additional_revenue,
            'costo_comision_bancaria': metrics['costo_comision_bancaria'],
            'costo_fee_plataforma': metrics['costo_fee_plataforma'],
            'costo_ingredientes': metrics['costo_ingredientes'],
            'total_costos_variables': metrics['total_costos_variables']
        })
    
    df_scenarios = pd.DataFrame(scenarios_df)
    
    # Display comparison table (Enhanced version like EZ-TEK)
    st.subheader("📊 Tabla de Comparación de Escenarios")
    
    # Create formatted display dataframe
    df_display = df_scenarios.copy()
    df_display['Revenue'] = df_display['ventas_mensuales'].apply(lambda x: f"${x:,.0f}")
    df_display['Orders'] = df_display['ordenes_mensuales'].apply(lambda x: f"{x:,.0f}")
    df_display['Contrib. Margin'] = df_display['margen_contribucion'].apply(lambda x: f"${x:,.0f}")
    df_display['Operating Profit'] = df_display['utilidad_operativa'].apply(lambda x: f"${x:,.0f}")
    df_display['Op. Margin'] = df_display['margen_operativo'].apply(lambda x: f"{x:.1f}%")
    
    st.dataframe(
        df_display[['scenario_name', 'total_tables', 'ticket_promedio', 'ocupacion_promedio', 'rotacion_diaria', 
                   'Revenue', 'Orders', 'Contrib. Margin', 'Operating Profit', 'Op. Margin']],
        hide_index=True,
        use_container_width=True
    )
    
    # Detailed breakdown for each scenario (Like EZ-TEK tabs)
    st.divider()
    st.header("🔍 Desglose Detallado del Escenario")
    
    tabs = st.tabs([scenario['scenario_name'] for scenario in scenarios_df])
    
    for idx, (tab, scenario) in enumerate(zip(tabs, scenarios_df)):
        with tab:
            # Header metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Ventas Mensuales", f"${scenario['ventas_mensuales']:,.0f}")
                st.metric("Órdenes/Mes", f"{scenario['ordenes_mensuales']:,.0f}")
            
            with col2:
                st.metric("Total Mesas", f"{scenario['total_tables']}")
                st.metric("Ticket Promedio", f"${scenario['ticket_promedio']}")
            
            with col3:
                st.metric("Utilidad Operativa", f"${scenario['utilidad_operativa']:,.0f}")
                profit_color = "🟢" if scenario['utilidad_operativa'] > 0 else "🔴"
                st.metric("Margen Operativo", f"{scenario['margen_operativo']:.1f}%")
            
            # Show improvements if not baseline
            if not scenario['is_baseline'] and baseline:
                st.subheader("📈 Mejoras en el Rendimiento vs Baseline")
                
                imp_col1, imp_col2 = st.columns(2)
                
                with imp_col1:
                    st.markdown("**Métricas Operativas:**")
                    
                    if scenario['improvements']['ticket_increase'] != 0:
                        color = "🟢" if scenario['improvements']['ticket_increase'] > 0 else "🔴"
                        st.markdown(f"{color} **Ticket Promedio:** {scenario['improvements']['ticket_increase']:+.1f}%")
                        if scenario['additional_revenue']['from_ticket'] != 0:
                            impact_text = "Ingreso Adicional" if scenario['additional_revenue']['from_ticket'] > 0 else "Pérdida de Ingreso"
                            st.write(f"{impact_text}: ${abs(scenario['additional_revenue']['from_ticket']):,.0f}")
                    
                    if scenario['improvements']['turnover_increase'] != 0:
                        color = "🟢" if scenario['improvements']['turnover_increase'] > 0 else "🔴"
                        st.markdown(f"{color} **Rotación por Mesa:** {scenario['improvements']['turnover_increase']:+.1f}%")
                        if scenario['additional_revenue']['from_turnover'] != 0:
                            impact_text = "Ingreso Adicional" if scenario['additional_revenue']['from_turnover'] > 0 else "Pérdida de Ingreso"
                            st.write(f"{impact_text}: ${abs(scenario['additional_revenue']['from_turnover']):,.0f}")
                
                with imp_col2:
                    st.markdown("**Métricas de Capacidad:**")
                    
                    if scenario['improvements']['occupancy_increase'] != 0:
                        color = "🟢" if scenario['improvements']['occupancy_increase'] > 0 else "🔴"
                        st.markdown(f"{color} **Ocupación:** {scenario['improvements']['occupancy_increase']:+.0f} pts")
                        if scenario['additional_revenue']['from_occupancy'] != 0:
                            impact_text = "Ingreso Adicional" if scenario['additional_revenue']['from_occupancy'] > 0 else "Pérdida de Ingreso"
                            st.write(f"{impact_text}: ${abs(scenario['additional_revenue']['from_occupancy']):,.0f}")
                    
                    if scenario['improvements']['tables_added'] != 0:
                        color = "🟢" if scenario['improvements']['tables_added'] > 0 else "🔴"
                        st.markdown(f"{color} **Mesas:** {scenario['improvements']['tables_added']:+.0f}")
                        if scenario['additional_revenue']['from_tables'] != 0:
                            impact_text = "Ingreso Adicional" if scenario['additional_revenue']['from_tables'] > 0 else "Pérdida de Ingreso"
                            st.write(f"{impact_text}: ${abs(scenario['additional_revenue']['from_tables']):,.0f}")
                
                # Total improvement summary
                attributed_revenue = sum(scenario['additional_revenue'].values())
                baseline_scenario = next(s for s in scenarios_df if s['is_baseline'])
                actual_revenue_difference = scenario['ventas_mensuales'] - baseline_scenario['ventas_mensuales']
                profit_increase = scenario['utilidad_operativa'] - baseline_scenario['utilidad_operativa']
                
                # Check if there are interaction effects
                if abs(attributed_revenue - actual_revenue_difference) > 1:  # Allow for small rounding differences
                    interaction_effect = actual_revenue_difference - attributed_revenue
                    st.info(f"💰 **Impacto Total Real:** ${actual_revenue_difference:+,.0f} | **Suma Atribuida:** ${attributed_revenue:+,.0f} | **Efecto Complementario:** ${interaction_effect:+,.0f}")
                    st.success(f"💰 **Ganancia Adicional:** ${profit_increase:+,.0f}")
                else:
                    st.success(f"💰 **Impacto Total:** Ingreso Adicional: ${actual_revenue_difference:+,.0f} | Ganancia Adicional: ${profit_increase:+,.0f}")
            
            # Configuración del escenario
            st.subheader("⚙️ Configuración del Escenario")
            
            config_col1, config_col2 = st.columns(2)
            
            with config_col1:
                st.markdown("**Configuración de Mesas por Día:**")
                days = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
                mesas_data = scenario_name in st.session_state.scenarios and st.session_state.scenarios[scenario_name].get('mesas_semana', [20]*7) or [20]*7
                
                for i, (day, tables) in enumerate(zip(days, mesas_data)):
                    st.write(f"{day}: {tables} mesas")
            
            with config_col2:
                st.markdown("**Parámetros Operativos:**")
                st.write(f"Días de Operación: {scenario['dias_operacion']}")
                st.write(f"Tasa de Ocupación: {scenario['ocupacion_promedio']}%")
                st.write(f"Rotación de Mesas: {scenario['rotacion_diaria']}")
                st.write(f"Ticket Promedio: ${scenario['ticket_promedio']}")
            
            # Resumen P&L (Mejorado como EZ-TEK)
            st.subheader("💼 Resumen P&L del Restaurante")
            
            pl_data = {
                'Concepto': [
                    'Ingresos',
                    'Comisión Bancaria',
                    'Fee EZ-TEK',
                    'Costo de Alimentos',
                    'Total Costos Variables',
                    'Margen de Contribución',
                    'Costos Fijos',
                    'Utilidad Operativa'
                ],
                'Monto': [
                    f"${scenario['ventas_mensuales']:,.0f}",
                    f"-${scenario['costo_comision_bancaria']:,.0f}",
                    f"-${scenario['costo_fee_plataforma']:,.0f}",
                    f"-${scenario['costo_ingredientes']:,.0f}",
                    f"-${scenario['total_costos_variables']:,.0f}",
                    f"${scenario['margen_contribucion']:,.0f}",
                    f"-${total_costos_fijos:,.0f}",
                    f"${scenario['utilidad_operativa']:,.0f}"
                ],
                '% de Ingresos': [
                    "100.0%",
                    f"{scenario['costo_comision_bancaria']/scenario['ventas_mensuales']*100:.1f}%",
                    f"{scenario['costo_fee_plataforma']/scenario['ventas_mensuales']*100:.1f}%",
                    f"{scenario['costo_ingredientes']/scenario['ventas_mensuales']*100:.1f}%",
                    f"{scenario['total_costos_variables']/scenario['ventas_mensuales']*100:.1f}%",
                    f"{scenario['margen_contribucion']/scenario['ventas_mensuales']*100:.1f}%",
                    f"{total_costos_fijos/scenario['ventas_mensuales']*100:.1f}%",
                    f"{scenario['margen_operativo']:.1f}%"
                ]
            }
            
            df_pl = pd.DataFrame(pl_data)
            st.dataframe(df_pl, hide_index=True, use_container_width=True)
    
    # Sección de visualización (Mejorada como EZ-TEK)
    st.divider()
    st.header("📊 Análisis Visual")
    
    viz_tab1, viz_tab2, viz_tab3 = st.tabs(["Comparación de Ingresos", "Desglose del Rendimiento", "Análisis de Rentabilidad"])
    
    with viz_tab1:
        # Create subplot with secondary y-axis for better visualization
        fig1 = make_subplots(specs=[[{"secondary_y": False}]])
        
        # Add revenue bars
        fig1.add_trace(go.Bar(
            x=df_scenarios['scenario_name'],
            y=df_scenarios['ventas_mensuales'],
            name='Ingresos Mensuales',
            marker_color=['#28a745' if x else '#4ECDC4' for x in df_scenarios['is_baseline']],
            text=[f"${x:,.0f}" for x in df_scenarios['ventas_mensuales']],
            textposition='auto',
            offsetgroup=1,
            width=0.4
        ))
        
        # Add profit bars
        fig1.add_trace(go.Bar(
            x=df_scenarios['scenario_name'],
            y=df_scenarios['utilidad_operativa'],
            name='Utilidad Operativa',
            marker_color=['#20c997' if x else '#98D8C8' for x in df_scenarios['is_baseline']],
            text=[f"${x:,.0f}" for x in df_scenarios['utilidad_operativa']],
            textposition='auto',
            offsetgroup=2,
            width=0.4
        ))
        
        fig1.update_layout(
            title="Comparación de Ingresos y Utilidad por Escenario",
            xaxis_title="Escenario",
            yaxis_title="Monto (MXN)",
            height=500,
            barmode='group',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        st.plotly_chart(fig1, use_container_width=True)
        
        # Add summary metrics below the chart
        st.subheader("📊 Resumen Comparativo")
        
        if baseline:
            baseline_scenario = next(s for s in scenarios_df if s['is_baseline'])
            
            summary_data = []
            for scenario in scenarios_df:
                if not scenario['is_baseline']:
                    revenue_diff = scenario['ventas_mensuales'] - baseline_scenario['ventas_mensuales']
                    profit_diff = scenario['utilidad_operativa'] - baseline_scenario['utilidad_operativa']
                    revenue_pct = (revenue_diff / baseline_scenario['ventas_mensuales'] * 100) if baseline_scenario['ventas_mensuales'] > 0 else 0;
                    
                    summary_data.append({
                        'Escenario': scenario['scenario_name'],
                        'Incremento en Ingresos': f"${revenue_diff:+,.0f} ({revenue_pct:+.1f}%)",
                        'Incremento en Utilidad': f"${profit_diff:+,.0f}",
                        'Margen Operativo': f"{scenario['margen_operativo']:.1f}%"
                    })
            
            if summary_data:
                df_summary = pd.DataFrame(summary_data)
                st.dataframe(df_summary, hide_index=True, use_container_width=True)

    with viz_tab2:
        # Show performance improvement details
        st.subheader("Componentes de Mejora del Rendimiento")
        
        for scenario in scenarios_df:
            if not scenario['is_baseline'] and any(abs(x) > 0 for x in scenario['additional_revenue'].values()):
                st.write(f"**{scenario['scenario_name']}:**")
                
                improvement_breakdown = []
                if scenario['additional_revenue']['from_ticket'] != 0:
                    impact_type = "Aumento" if scenario['additional_revenue']['from_ticket'] > 0 else "Reducción"
                    improvement_breakdown.append(f"{impact_type} por Ticket: ${abs(scenario['additional_revenue']['from_ticket']):,.0f}")
                if scenario['additional_revenue']['from_occupancy'] != 0:
                    impact_type = "Aumento" if scenario['additional_revenue']['from_occupancy'] > 0 else "Reducción"
                    improvement_breakdown.append(f"{impact_type} por Ocupación: ${abs(scenario['additional_revenue']['from_occupancy']):,.0f}")
                if scenario['additional_revenue']['from_turnover'] != 0:
                    impact_type = "Aumento" if scenario['additional_revenue']['from_turnover'] > 0 else "Reducción"
                    improvement_breakdown.append(f"{impact_type} por Rotación: ${abs(scenario['additional_revenue']['from_turnover']):,.0f}")
                if scenario['additional_revenue']['from_tables'] != 0:
                    impact_type = "Aumento" if scenario['additional_revenue']['from_tables'] > 0 else "Reducción"
                    improvement_breakdown.append(f"{impact_type} por Mesas: ${abs(scenario['additional_revenue']['from_tables']):,.0f}")
                
                if improvement_breakdown:
                    st.write(" | ".join(improvement_breakdown))
                else:
                    st.write("No se detectaron cambios en el rendimiento")
    
    with viz_tab3:
        fig3 = make_subplots(specs=[[{"secondary_y": True}]])
        
        fig3.add_trace(
            go.Bar(
                x=df_scenarios['scenario_name'],
                y=df_scenarios['utilidad_operativa'],
                name="Utilidad Operativa",
                marker_color=['#28a745' if x > 0 else '#dc3545' for x in df_scenarios['utilidad_operativa']]
            ),
            secondary_y=False,
        )
        
        fig3.add_trace(
            go.Scatter(
                x=df_scenarios['scenario_name'],
                y=df_scenarios['margen_operativo'],
                mode='lines+markers',
                name="Margen Operativo %",
                line=dict(color='#FF6B6B', width=3),
                marker=dict(size=10)
            ),
            secondary_y=True,
        )
        
        fig3.update_xaxes(title_text="Escenario")
        fig3.update_yaxes(title_text="Utilidad Operativa (MXN)", secondary_y=False)
        fig3.update_yaxes(title_text="Margen Operativo (%)", secondary_y=True)
        fig3.update_layout(title_text="Rentabilidad por Escenario", height=400)
        
        st.plotly_chart(fig3, use_container_width=True)
    
    # Análisis de la Propuesta de Valor (Como la sección de ROI de EZ-TEK)
    st.divider()
    st.header("💡 Análisis del Impacto en el Rendimiento")
    
    if baseline:
        st.subheader("Rendimiento del Escenario vs Baseline")
        
        baseline_scenario = next(s for s in scenarios_df if s['is_baseline'])
        
        for scenario in scenarios_df:
            if not scenario['is_baseline']:
                revenue_increase = scenario['ventas_mensuales'] - baseline_scenario['ventas_mensuales']
                profit_increase = scenario['utilidad_operativa'] - baseline_scenario['utilidad_operativa']
                
                # Detalle de mejoras en el rendimiento
                improvements_summary = []
                if scenario['improvements']['ticket_increase'] != 0:
                    improvements_summary.append(f"Ticket: {scenario['improvements']['ticket_increase']:+.1f}%")
                if scenario['improvements']['occupancy_increase'] != 0:
                    improvements_summary.append(f"Ocupación: {scenario['improvements']['occupancy_increase']:+.0f} pts")
                if scenario['improvements']['turnover_increase'] != 0:
                    improvements_summary.append(f"Rotación: {scenario['improvements']['turnover_increase']:+.1f}%")
                if scenario['improvements']['tables_added'] != 0:
                    improvements_summary.append(f"Mesas: {scenario['improvements']['tables_added']:+.0f}")
                
                # Calculate detailed revenue breakdown (matching the other section)
                total_additional_revenue_impact = sum(scenario['additional_revenue'].values())
                
                # Create breakdown similar to Section 1
                revenue_breakdown = []
                if scenario['additional_revenue']['from_ticket'] != 0:
                    sign = "+" if scenario['additional_revenue']['from_ticket'] > 0 else ""
                    revenue_breakdown.append(f"Ticket: {sign}${scenario['additional_revenue']['from_ticket']:,.0f}")
                if scenario['additional_revenue']['from_occupancy'] != 0:
                    sign = "+" if scenario['additional_revenue']['from_occupancy'] > 0 else ""
                    revenue_breakdown.append(f"Ocupación: {sign}${scenario['additional_revenue']['from_occupancy']:,.0f}")
                if scenario['additional_revenue']['from_turnover'] != 0:
                    sign = "+" if scenario['additional_revenue']['from_turnover'] > 0 else ""
                    revenue_breakdown.append(f"Rotación: {sign}${scenario['additional_revenue']['from_turnover']:,.0f}")
                if scenario['additional_revenue']['from_tables'] != 0:
                    sign = "+" if scenario['additional_revenue']['from_tables'] > 0 else ""
                    revenue_breakdown.append(f"Mesas: {sign}${scenario['additional_revenue']['from_tables']:,.0f}")
                
                st.markdown(f"""
                **{scenario['scenario_name']}:**
                - **Cambios en el Rendimiento**: {' | '.join(improvements_summary) if improvements_summary else 'Sin cambios'}
                - **Desglose de Ingresos Adicionales**: {' | '.join(revenue_breakdown) if revenue_breakdown else 'Sin ingresos adicionales'}
                - **Total Ingreso Adicional**: ${revenue_increase:,.0f}
                - **Ganancia Adicional**: ${profit_increase:,.0f}
                - **Impacto en Ingresos**: {(revenue_increase/baseline_scenario['ventas_mensuales']*100):+.1f}%
                """)

else:
    st.info("👆 Agrega tu primer escenario arriba para comenzar el análisis")

st.divider()
st.markdown("""
### 📝 Resumen del Análisis de Escenarios:
- **Escenario Base**: Punto de referencia para medir mejoras en el rendimiento
- **Indicadores de Rendimiento**: Promedio de ticket, tasa de ocupación, rotación de mesas, expansión de capacidad
- **Análisis de Impacto**: Impacto en ingresos y ganancias de las mejoras operativas
- **Enfoque del Restaurante**: Optimizado para operaciones de restaurantes y análisis de rentabilidad
""")

st.divider()

# =============================================================================
# CONTACT SECTION - WHATSAPP
# ==============================================================================

st.header("📞 ¿Necesitas Ayuda?")

# Contact section with WhatsApp
st.subheader("💬 Contáctanos por WhatsApp")

st.write("""
¿Tienes dudas sobre la plataforma EZ-TEK o necesitas asesoría personalizada?

**Nuestro equipo está listo para ayudarte con:**

✅ Configuración de tu restaurante
✅ Interpretación de métricas
✅ Estrategias de optimización
✅ Planes de expansión
✅ Integración con sistemas existentes

**¡Escríbenos ahora y recibe respuesta inmediata!**
""")

# WhatsApp button
st.link_button(
    "💬 Abrir WhatsApp",
    "https://wa.link/kr9cxy",
    use_container_width=True,
    type="primary"
)

st.success("📱 Atención 24/7 - Disponible todos los días")

# =============================================================================
# COMPREHENSIVE EXCEL DOWNLOAD SECTION - HIDDEN
# ==============================================================================

# st.header("📥 Descargar Análisis Completo en Excel")

# Create comprehensive Excel export (hidden but functional)
def create_comprehensive_excel():
    """Create a comprehensive Excel file with all app data and analysis"""
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#4ECDC4',
            'border': 1,
            'font_color': 'white'
        })
        
        currency_format = workbook.add_format({
            'num_format': '$#,##0',
            'border': 1
        })
        
        percent_format = workbook.add_format({
            'num_format': '0.0%',
            'border': 1
        })
        
        number_format = workbook.add_format({
            'num_format': '#,##0.0',
            'border': 1
        })
        
        text_format = workbook.add_format({
            'border': 1,
            'text_wrap': True
        })
        
        # Sheet 1: Configuration Summary
        config_data = {
            'Parámetro': [
                'Ticket Promedio (MXN)',
                'Ocupación Promedio (%)',
                'Rotación por Mesa/Día',
                'Días de Operación/Mes',
                'Mesas Lunes',
                'Mesas Martes',
                'Mesas Miércoles',
                'Mesas Jueves',
                'Mesas Viernes',
                'Mesas Sábado',
                'Mesas Domingo',
                'Total Mesas Semana',
                'Comisión Bancaria (%)',
                'Fee EZ-TEK (%)',
                'Costo Ingredientes (%)',
                'Personal (MXN)',
                'Renta y Servicios (MXN)',
                'Tecnología (MXN)',
                'Marketing (MXN)',
                'Otros Gastos (MXN)',
                'Total Costos Fijos (MXN)',
                'Número de Ubicaciones'
            ],
            'Valor': [
                ticket_promedio,
                ocupacion_promedio,
                rotacion_diaria,
                dias_operacion,
                mesas_lunes,
                mesas_martes,
                mesas_miercoles,
                mesas_jueves,
                mesas_viernes,
                mesas_sabado,
                mesas_domingo,
                metricas['total_mesas'],
                comision_bancaria,
                fee_plataforma,
                costo_ingredientes,
                personal,
                renta,
                tecnologia,
                marketing,
                otros_gastos,
                total_costos_fijos,
                num_ubicaciones
            ]
        }
        
        df_config = pd.DataFrame(config_data)
        df_config.to_excel(writer, sheet_name='Configuracion', index=False, startrow=1, startcol=1)
        
        worksheet = writer.sheets['Configuracion']
        worksheet.write(0, 1, 'CONFIGURACIÓN DEL RESTAURANTE', header_format)
        worksheet.set_column('B:B', 25)
        worksheet.set_column('C:C', 15)
        
        # Sheet 2: Main Metrics Summary
        main_metrics = {
            'Métrica': [
                'Ventas Mensuales',
                'Órdenes Mensuales',
                'Ingresos Brutos',
                'Costo Comisión Bancaria',
                'Costo Fee EZ-TEK',
                'Costo Ingredientes',
                'Total Costos Variables',
                'Contribución Marginal',
                'Contribución Marginal %',
                'Total Costos Fijos',
                'Utilidad Operativa',
                'Margen Operativo %'
            ],
            'Valor': [
                metricas['ventas_mensuales'],
                metricas['ordenes_mensuales'],
                rentabilidad['ingresos_brutos'],
                rentabilidad['costo_comision_bancaria'],
                rentabilidad['costo_fee_plataforma'],
                rentabilidad['costo_ingredientes'],
                rentabilidad['total_costos_variables'],
                rentabilidad['margen_contribucion'],
                rentabilidad['margen_contribucion_pct'] / 100,
                total_costos_fijos,
                rentabilidad['utilidad_operativa'],
                rentabilidad['margen_operativo_pct'] / 100
            ],
            'Fórmula/Explicación': [
                'Órdenes × Ticket Promedio × Días Operación',
                'Mesas × Ocupación × Rotación × Días',
                'Ventas Mensuales',
                f'Ingresos × {comision_bancaria}%',
                f'Ingresos × {fee_plataforma}%',
                f'Ingresos × {costo_ingredientes}%',
                'Comisión + Fee + Ingredientes',
                'Ingresos - Costos Variables',
                'Contribución Marginal / Ingresos',
                'Personal + Renta + Tecnología + Marketing + Otros',
                'Contribución Marginal - Costos Fijos',
                'Utilidad Operativa / Ingresos'
            ]
        }
        
        df_main = pd.DataFrame(main_metrics)
        df_main.to_excel(writer, sheet_name='Metricas_Principales', index=False, startrow=1, startcol=1)
        
        worksheet = writer.sheets['Metricas_Principales']
        worksheet.write(0, 1, 'MÉTRICAS PRINCIPALES DEL RESTAURANTE', header_format)
        worksheet.set_column('B:B', 25)
        worksheet.set_column('C:C', 20, currency_format)
        worksheet.set_column('D:D', 40)
        
        # Sheet 3: Weekly Analysis
        df_weekly = pd.DataFrame(metricas['metricas_diarias'])
        df_weekly['ventas_dia_formatted'] = df_weekly['ventas_dia']
        df_weekly['ordenes_dia_formatted'] = df_weekly['ordenes_dia']
        
        df_weekly_export = df_weekly[['dia', 'mesas_disponibles', 'mesas_ocupadas', 'ordenes_dia_formatted', 'ventas_dia_formatted']].copy()
        df_weekly_export.columns = ['Día', 'Mesas Disponibles', 'Mesas Ocupadas', 'Órdenes/Día', 'Ventas/Día']
        
        df_weekly_export.to_excel(writer, sheet_name='Analisis_Semanal', index=False, startrow=1, startcol=1)
        
        worksheet = writer.sheets['Analisis_Semanal']
        worksheet.write(0, 1, 'ANÁLISIS SEMANAL DE OPERACIONES', header_format)
        worksheet.set_column('B:B', 12)
        worksheet.set_column('C:C', 18)
        worksheet.set_column('D:D', 16)
        worksheet.set_column('E:E', 15, number_format)
        worksheet.set_column('F:F', 15, currency_format)
        
        # Sheet 4: P&L Structure
        pl_structure = {
            'Concepto': [
                'Ingresos Brutos',
                'Comisión Bancaria',
                'Fee EZ-TEK',
                'Costo Ingredientes',
                'Total Costos Variables',
                'Contribución Marginal',
                'Personal',
                'Renta y Servicios',
                'Tecnología',
                'Marketing',
                'Otros Gastos',
                'Total Costos Fijos',
                'Utilidad Operativa'
            ],
            'Monto': [
                rentabilidad['ingresos_brutos'],
                -rentabilidad['costo_comision_bancaria'],
                -rentabilidad['costo_fee_plataforma'],
                -rentabilidad['costo_ingredientes'],
                -rentabilidad['total_costos_variables'],
                rentabilidad['margen_contribucion'],
                -personal,
                -renta,
                -tecnologia,
                -marketing,
                -otros_gastos,
                -total_costos_fijos,
                rentabilidad['utilidad_operativa']
            ],
            'Porcentaje': [
                100.0,
                -comision_bancaria,
                -fee_plataforma,
                -costo_ingredientes,
                -(rentabilidad['total_costos_variables']/rentabilidad['ingresos_brutos']*100),
                rentabilidad['margen_contribucion_pct'],
                -(personal/rentabilidad['ingresos_brutos']*100),
                -(renta/rentabilidad['ingresos_brutos']*100),
                -(tecnologia/rentabilidad['ingresos_brutos']*100),
                -(marketing/rentabilidad['ingresos_brutos']*100),
                -(otros_gastos/rentabilidad['ingresos_brutos']*100),
                -(total_costos_fijos/rentabilidad['ingresos_brutos']*100),
                rentabilidad['margen_operativo_pct']
            ]
        }
        
        df_pl = pd.DataFrame(pl_structure)
        df_pl.to_excel(writer, sheet_name='Estructura_PL', index=False, startrow=1, startcol=1)
        
        worksheet = writer.sheets['Estructura_PL']
        worksheet.write(0, 1, 'ESTRUCTURA P&L DETALLADA', header_format)
        worksheet.set_column('B:B', 25)
        worksheet.set_column('C:C', 20, currency_format)
        worksheet.set_column('D:D', 15, percent_format)
        
        # Sheet 5: Expansion Projections
        df_expansion = pd.DataFrame(proyecciones)
        df_expansion.columns = ['Ubicaciones', 'Ventas Mensuales', 'Utilidad Operativa', 'Margen Operativo %']
        df_expansion['Margen Operativo %'] = df_expansion['Margen Operativo %'] / 100
        
        df_expansion.to_excel(writer, sheet_name='Proyeccion_Expansion', index=False, startrow=1, startcol=1)
        
        worksheet = writer.sheets['Proyeccion_Expansion']
        worksheet.write(0, 1, 'PROYECCIÓN DE EXPANSIÓN GEOGRÁFICA', header_format)
        worksheet.set_column('B:B', 15)
        worksheet.set_column('C:C', 20, currency_format)
        worksheet.set_column('D:D', 20, currency_format)
        worksheet.set_column('E:E', 18, percent_format)
        
        # Sheet 6: Sensitivity Analysis
        break_even_orders = total_costos_fijos / (ticket_promedio * (1 - (comision_bancaria + fee_plataforma + costo_ingredientes)/100))
        
        sensitivity_points = [
            int(break_even_orders * 0.8),
            int(break_even_orders),
            int(metricas['ordenes_mensuales']),
            int(break_even_orders * 1.2),
            int(break_even_orders * 1.5)
        ]
        
        sensitivity_data = []
        for orders in sensitivity_points:
            ventas = orders * ticket_promedio
            rent = calcular_rentabilidad(ventas)
            
            if orders < break_even_orders:
                scenario_type = "Por debajo del equilibrio"
            elif orders == int(break_even_orders):
                scenario_type = "Punto de equilibrio"
            elif orders == int(metricas['ordenes_mensuales']):
                scenario_type = "Situación actual"
            else:
                scenario_type = "Por encima del equilibrio"
            
            sensitivity_data.append({
                'Escenario': scenario_type,
                'Órdenes Mensuales': orders,
                'Ventas Mensuales': ventas,
                'Utilidad Operativa': rent['utilidad_operativa'],
                'Margen Operativo %': rent['margen_operativo_pct'] / 100
            })
        
        df_sensitivity = pd.DataFrame(sensitivity_data)
        df_sensitivity.to_excel(writer, sheet_name='Analisis_Sensibilidad', index=False, startrow=1, startcol=1)
        
        worksheet = writer.sheets['Analisis_Sensibilidad']
        worksheet.write(0, 1, 'ANÁLISIS DE SENSIBILIDAD POR ÓRDENAS', header_format)
        worksheet.set_column('B:B', 25)
        worksheet.set_column('C:C', 18, number_format)
        worksheet.set_column('D:D', 20, currency_format)
        worksheet.set_column('E:E', 20, currency_format)
        worksheet.set_column('F:F', 18, percent_format)
        
        # Sheet 7: Scenario Comparisons (if scenarios exist)
        if st.session_state.scenarios:
            scenarios_export = []
            
            for scenario_name, scenario_data in st.session_state.scenarios.items():
                metrics = calculate_scenario_metrics(scenario_data)
                total_tables = sum(scenario_data['mesas_semana'])
                
                scenarios_export.append({
                    'Nombre_Escenario': scenario_name,
                    'Es_Baseline': 'Sí' if scenario_data.get('is_baseline', False) else 'No',
                    'Ticket_Promedio': scenario_data['ticket_promedio'],
                    'Ocupacion_Promedio': scenario_data['ocupacion_promedio'],
                    'Rotacion_Mesa_Dia': scenario_data['rotacion_diaria'],
                    'Dias_Operacion_Mes': scenario_data['dias_operacion'],
                    'Total_Mesas': total_tables,
                    'Mesas_Lunes': scenario_data['mesas_semana'][0],
                    'Mesas_Martes': scenario_data['mesas_semana'][1],
                    'Mesas_Miercoles': scenario_data['mesas_semana'][2],
                    'Mesas_Jueves': scenario_data['mesas_semana'][3],
                    'Mesas_Viernes': scenario_data['mesas_semana'][4],
                    'Mesas_Sabado': scenario_data['mesas_semana'][5],
                    'Mesas_Domingo': scenario_data['mesas_semana'][6],
                    'Ordenes_Mensuales': metrics['ordenes_mensuales'],
                    'Ventas_Mensuales': metrics['ventas_mensuales'],
                    'Contribucion_Marginal': metrics['margen_contribucion'],
                    'Contribucion_Marginal_Pct': metrics['margen_contribucion_pct'] / 100,
                    'Utilidad_Operativa': metrics['utilidad_operativa'],
                    'Margen_Operativo_Pct': metrics['margen_operativo_pct'] / 100,
                    'Costo_Comision_Bancaria': metrics['costo_comision_bancaria'],
                    'Costo_Fee_Plataforma': metrics['costo_fee_plataforma'],
                    'Costo_Ingredientes': metrics['costo_ingredientes'],
                    'Total_Costos_Variables': metrics['total_costos_variables'],
                    'Fecha_Creacion': scenario_data.get('created_at', datetime.now()).strftime('%Y-%m-%d %H:%M:%S')
                })
            
            df_scenarios_export = pd.DataFrame(scenarios_export)
            df_scenarios_export.to_excel(writer, sheet_name='Escenarios_Comparacion', index=False, startrow=1, startcol=1)
            
            worksheet = writer.sheets['Escenarios_Comparacion']
            worksheet.write(0, 1, 'COMPARACIÓN DE ESCENARIOS', header_format)
            
            worksheet.set_column('B:B', 20)
            worksheet.set_column('C:C', 12)
            worksheet.set_column('D:D', 15, currency_format)
            worksheet.set_column('E:E', 15, percent_format)
            worksheet.set_column('F:F', 15, number_format)
            worksheet.set_column('G:G', 15, number_format)
            worksheet.set_column('H:H', 12)
            worksheet.set_column('I:O', 12)
            worksheet.set_column('P:P', 18, number_format)
            worksheet.set_column('Q:Q', 18, currency_format)
            worksheet.set_column('R:R', 18, currency_format)
            worksheet.set_column('S:S', 18, percent_format)
            worksheet.set_column('T:T', 18, currency_format)
            worksheet.set_column('U:U', 18, percent_format)
            worksheet.set_column('V:Y', 18, currency_format)
            worksheet.set_column('Z:Z', 20)
            
            # Sheet 8: Scenario Improvements Analysis
            if len(st.session_state.scenarios) > 1:
                # --- MODIFIED: Prioritize the auto-generated baseline ---
                baseline = None
                baseline_name = None
                for scenario_name, scenario_data in st.session_state.scenarios.items():
                    if scenario_data.get('auto_generated', False):
                        baseline = scenario_data
                        baseline_name = scenario_name
                        break
                
                if baseline is None: # Fallback if auto-generated is missing
                    for scenario_name, scenario_data in st.session_state.scenarios.items():
                        if scenario_data.get('is_baseline', False):
                            baseline = scenario_data
                            baseline_name = scenario_name
                            break
                
                if baseline:
                    baseline_metrics = calculate_scenario_metrics(baseline)
                    baseline_total_tables = sum(baseline['mesas_semana'])
                    
                    improvements_export = []
                    
                    for scenario_name, scenario_data in st.session_state.scenarios.items():
                        if scenario_name != baseline_name:
                            metrics = calculate_scenario_metrics(scenario_data)
                            total_tables = sum(scenario_data['mesas_semana'])
                            
                            ticket_increase = ((scenario_data['ticket_promedio'] - baseline['ticket_promedio']) / baseline['ticket_promedio'] * 100) if baseline['ticket_promedio'] > 0 else 0
                            occupancy_increase = scenario_data['ocupacion_promedio'] - baseline['ocupacion_promedio']
                            turnover_increase = ((scenario_data['rotacion_diaria'] - baseline['rotacion_diaria']) / baseline['rotacion_diaria'] * 100) if baseline['rotacion_diaria'] > 0 else 0
                            tables_added = total_tables - baseline_total_tables
                            revenue_increase = ((metrics['ventas_mensuales'] - baseline_metrics['ventas_mensuales']) / baseline_metrics['ventas_mensuales'] * 100) if baseline_metrics['ventas_mensuales'] > 0 else 0
                            profit_increase = metrics['utilidad_operativa'] - baseline_metrics['utilidad_operativa']
                            
                            improvements_export.append({
                                'Escenario': scenario_name,
                                'Baseline_Ticket': baseline['ticket_promedio'],
                                'Escenario_Ticket': scenario_data['ticket_promedio'],
                                'Mejora_Ticket_Pct': ticket_increase / 100,
                                'Baseline_Ocupacion': baseline['ocupacion_promedio'],
                                'Escenario_Ocupacion': scenario_data['ocupacion_promedio'],
                                'Mejora_Ocupacion_Pts': occupancy_increase,
                                'Baseline_Rotacion': baseline['rotacion_diaria'],
                                'Escenario_Rotacion': scenario_data['rotacion_diaria'],
                                'Mejora_Rotacion_Pct': turnover_increase / 100,
                                'Baseline_Mesas': baseline_total_tables,
                                'Escenario_Mesas': total_tables,
                                'Mesas_Agregadas': tables_added,
                                'Baseline_Ingresos': baseline_metrics['ventas_mensuales'],
                                'Escenario_Ingresos': metrics['ventas_mensuales'],
                                'Mejora_Ingresos_Pct': revenue_increase / 100,
                                'Baseline_Utilidad': baseline_metrics['utilidad_operativa'],
                                'Escenario_Utilidad': metrics['utilidad_operativa'],
                                'Mejora_Utilidad_Absoluta': profit_increase
                            })
                    
                    if improvements_export:
                        df_improvements = pd.DataFrame(improvements_export)
                        df_improvements.to_excel(writer, sheet_name='Mejoras_vs_Baseline', index=False, startrow=1, startcol=1)
                        
                        worksheet = writer.sheets['Mejoras_vs_Baseline']
                        worksheet.write(0, 1, 'ANÁLISIS DE MEJORAS VS BASELINE', header_format)
                        
                        worksheet.set_column('B:B', 20)
                        worksheet.set_column('C:C', 15, currency_format)
                        worksheet.set_column('D:D', 15, currency_format)
                        worksheet.set_column('E:E', 18, percent_format)
                        worksheet.set_column('F:F', 15, percent_format)
                        worksheet.set_column('G:G', 15, percent_format)
                        worksheet.set_column('H:H', 18, number_format)
                        worksheet.set_column('I:I', 15, number_format)
                        worksheet.set_column('J:J', 15, number_format)
                        worksheet.set_column('K:K', 18, percent_format)
                        worksheet.set_column('L:L', 15, number_format)
                        worksheet.set_column('M:M', 15, number_format)
                        worksheet.set_column('N:N', 15, number_format)
                        worksheet.set_column('O:O', 20, currency_format)
                        worksheet.set_column('P:P', 20, currency_format)
                        worksheet.set_column('Q:Q', 20, percent_format)
                        worksheet.set_column('R:R', 20, currency_format)
                        worksheet.set_column('S:S', 20, currency_format)
                        worksheet.set_column('T:T', 20, currency_format)
        
        # Sheet 9: Executive Summary
        exec_summary = {
            'Métrica Clave': [
                'RESUMEN EJECUTIVO',
                '',
                'Configuración Actual',
                'Ticket Promedio',
                'Ocupación Promedio',
                'Rotación por Mesa',
                'Total Mesas',
                'Días de Operación',
                '',
                'Resultados Financieros',
                'Ventas Mensuales',
                'Órdenes Mensuales',
                'Contribución Marginal',
                'Utilidad Operativa',
                'Margen Operativo',
                '',
                'Análisis de Punto de Equilibrio',
                'Órdenes Necesarias para Equilibrio',
                'Diferencia vs Actual',
                'Contribución por Orden',
                '',
                'Escenarios Analizados',
                f'Total de Escenarios Creados: {len(st.session_state.scenarios)}',
                f'Baseline Establecido: {"Sí" if st.session_state.baseline_set else "No"}',
                '',
                'Fecha de Análisis',
                f'Generado el: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
            ],
            'Valor': [
                '',
                '',
                '',
                f'${ticket_promedio}',
                f'{ocupacion_promedio}%',
                f'{rotacion_diaria}x',
                f'{metricas["total_mesas"]}',
                f'{dias_operacion} días',
                '',
                '',
                f'${metricas["ventas_mensuales"]:,.0f}',
                f'{metricas["ordenes_mensuales"]:,.0f}',
                f'${rentabilidad["margen_contribucion"]:,.0f}',
                f'${rentabilidad["utilidad_operativa"]:,.0f}',
                f'{rentabilidad["margen_operativo_pct"]:.1f}%',
                '',
                '',
                f'{break_even_orders:,.0f}',
                f'{metricas["ordenes_mensuales"] - break_even_orders:+,.0f}',
                f'${ticket_promedio * (1 - (comision_bancaria + fee_plataforma + costo_ingredientes)/100):,.2f}',
                '',
                '',
                '',
                '',
                '',
                '',
                ''
            ]
        }
        
        df_summary = pd.DataFrame(exec_summary)
        df_summary.to_excel(writer, sheet_name='Resumen_Ejecutivo', index=False, startrow=1, startcol=1)
        
        worksheet = writer.sheets['Resumen_Ejecutivo']
        worksheet.write(0, 1, 'RESUMEN EJECUTIVO DEL ANÁLISIS', header_format)
        worksheet.set_column('B:B', 35)
        worksheet.set_column('C:C', 25)
        
        worksheet.conditional_format('C1:C50', {
            'type': 'text',
            'criteria': 'containing',
            'value': '+',
            'format': workbook.add_format({'bg_color': '#90EE90'})
        })
        
        worksheet.conditional_format('C1:C50', {
            'type': 'text',
            'criteria': 'containing',
            'value': '-',
            'format': workbook.add_format({'bg_color': '#FFB6C1'})
        })
    
    return output.getvalue()

# HIDDEN: Display download section
# col1, col2 = st.columns([2, 1])
# 
# with col1:
#     st.subheader("📊 Análisis Completo del Restaurante")
#     
#     # Count total sheets
#     sheet_count = 6  # Base sheets
#     if st.session_state.scenarios:
#         sheet_count += 1  # Scenario comparison
#         if len(st.session_state.scenarios) > 1:
#             sheet_count += 1  # Improvements analysis
#     sheet_count += 1  # Executive summary
#     
#     st.write(f"""
#     **El archivo Excel incluye {sheet_count} hojas con:**
#     
#     📋 **Configuración**: Todos los parámetros del restaurante
#     📊 **Métricas Principales**: KPIs y fórmulas de cálculo
#     📅 **Análisis Semanal**: Desglose por día de la semana
#     💹 **Estructura P&L**: Estado de resultados detallado
#     🚀 **Proyección Expansión**: Escalabilidad del negocio
#     📈 **Análisis Sensibilidad**: Punto de equilibrio y escenarios
#     """)
#     
#     if st.session_state.scenarios:
#         st.write(f"""
#         🔄 **Comparación Escenarios**: {len(st.session_state.scenarios)} escenarios analizados
#         """)
#         
#         if len(st.session_state.scenarios) > 1:
#             st.write("""
#             📈 **Análisis de Mejoras**: Comparación detallada vs baseline
#             """)
#     
#     st.write("""
#     📋 **Resumen Ejecutivo**: Dashboard completo con métricas clave
#     """)
# 
# with col2:
#     st.subheader("⬇️ Descargar")
#     
#     # Generate filename
#     timestamp = datetime.now().strftime("%Y%m%d_%H%M")
#     scenarios_suffix = f"_{len(st.session_state.scenarios)}escenarios" if st.session_state.scenarios else ""
#     filename = f"Restaurant_Analysis_Complete_{timestamp}{scenarios_suffix}.xlsx"
#     
#     # Download button
#     excel_data = create_comprehensive_excel()
#     
#     st.download_button(
#         label="📥 Descargar Análisis Completo",
#         data=excel_data,
#         file_name=filename,
#         mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#         use_container_width=True,
#         help=f"Descarga un archivo Excel completo con {sheet_count} hojas de análisis"
#     )
#     
#     st.info(f"**Archivo:** {filename}")
#     st.success(f"✅ **{sheet_count} hojas** de análisis completo")
# 
# # HIDDEN: Contenido del Archivo Excel description
# # st.divider()
# # st.markdown("""
# # ### 📁 Contenido del Archivo Excel:
# # - **Configuración completa** del restaurante con todos los parámetros
# # - **Métricas financieras** con fórmulas y explicaciones
# # - **Análisis operativo** por día de la semana
# # - **Estado de resultados** detallado y cascada P&L
# # - **Proyecciones de expansión** para múltiples ubicaciones
# # - **Análisis de sensibilidad** con punto de equilibrio
# # - **Comparación de escenarios** (si existen)
# # - **Análisis de mejoras** vs baseline (si aplica)
# # - **Resumen ejecutivo** con métricas clave
# # 
# # Este reporte ejecutivo está listo para presentaciones gerenciales y toma de decisiones estratégicas.
# """)
