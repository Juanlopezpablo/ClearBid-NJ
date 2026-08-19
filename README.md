# ClearBid NJ · Pre-Bid Real Estate Intelligence Platform

> **Asignatura:** Proyecto Capstone 2026 (APT)  
> **Escuela:** Informática y Telecomunicaciones  
> **Estado:** Fase 1 - Definición y Arquitectura

---

## 📌 Descripción del Proyecto

### ¿Qué es ClearBid NJ?
**ClearBid NJ** es una plataforma web orientada a la inteligencia inmobiliaria previa a pujas (*pre-bid intelligence*), diseñada específicamente para inversores que participan en subastas judiciales (*sheriff sales*) en el estado de New Jersey, Estados Unidos.

### ¿Qué problema resuelve?
Participar en remates judiciales implica un riesgo financiero crítico: la existencia de gravámenes ocultos (*hidden liens*), deudas impositivas municipales (*tax liens*) y gravámenes que sobreviven a la ejecución judicial. La falta de acceso centralizado a esta información suele provocar pérdidas sustanciales de capital. 

ClearBid NJ centraliza los expedientes de subasta, ejecuta un motor de reglas determinista para auditar gravámenes y calcula automáticamente:
* **Semáforo de Riesgo (Score):** Indicador visual (Verde / Amarillo / Rojo) sobre la viabilidad jurídica y financiera de la propiedad.
* **MAO (*Maximum Allowable Offer*):** Cálculo dinámico del precio máximo que un inversor debería ofertar considerando costos de reparación, gravámenes pendientes y margen de ganancia esperado.

### ¿A quién va dirigido?
* Inversores individuales en bienes raíces residenciales y comerciales.
* Fondos de inversión inmobiliaria y compradores institucionales.
* Analistas de riesgo y agentes de *due diligence*.

---

## 👥 Integrantes del Equipo y Roles

| Nombre Completo | Rol en el Proyecto | Correo Institucional | Perfil GitHub |
| :--- | :--- | :--- | :--- |
| Juan Pablo Lopez Peña | Product Owner & Backend Lead | [jua.lopezp@duocuc.cl] | https://github.com/Juanlopezpablo |
| [Daniela Belen Cuevas Chavez] | Scrum Master & Frontend Lead | Dani.cuevasc@duocuc.cl https://github.com/dani-cuevas |


---

## 🛠️ Tecnologías Utilizadas

* **Frontend:** React 18+, TypeScript / JavaScript, Vite, Tailwind CSS, TanStack Query.
* **Backend:** Python 3.11+, FastAPI (REST API), SQLAlchemy (ORM), Pydantic (Validaciones), Alembic (Migraciones).
* **Base de Datos:** PostgreSQL 15+.
* **Contenerización & Entorno:** Docker, Docker Compose.
* **Control de Versiones y CI/CD:** Git, GitHub Actions.

---

## 🏛️ Arquitectura de la Solución

La solución sigue una arquitectura desacoplada por capas y basada en microservicios contenerizados:
┌──────────────────────────────────────────────────────────┐
│                   Cliente Web (Browser)                  │
└────────────────────────────┬─────────────────────────────┘
│ (HTTP / JSON REST)
▼
┌──────────────────────────────────────────────────────────┐
│              Frontend Service (React + Vite)             │
│               Puerto Local: 3000 / Nginx                 │
└────────────────────────────┬─────────────────────────────┘
│ (API Requests)
▼
┌──────────────────────────────────────────────────────────┐
│               Backend API (FastAPI / Python)             │
│  - Reglas de Negocio / Motor de Riesgo                   │
│  - Calculadora MAO (Maximum Allowable Offer)             │
│  - Endpoints CRUD de Propiedades y Liens                 │
└────────────────────────────┬─────────────────────────────┘
│ (SQLAlchemy ORM)
▼
┌──────────────────────────────────────────────────────────┐
│              Base de Datos (PostgreSQL 15+)              │
│       Esquema relacional: Propiedades, Liens, Users      │
└──────────────────────────────────────────────────────────┘
---

## 🔄 Metodología de Trabajo

El equipo aplica el marco de trabajo **Scrum**:
* **Sprints:** Ciclos iterativos de 2 semanas orientados a entregables funcionales.
* **Gestión Visual:** Seguimiento de historias de usuario, tareas y *Definition of Done (DoD)* a través de **GitHub Projects** y **GitHub Issues**.
* **Estrategia Git:** Flujo basado en ramas de características (*feature branches*) y revisiones vía *Pull Requests (PR)* con validación de pruebas.

## 🚀 Instrucciones para Ejecutar el Proyecto Localmente

### Prerrequisitos
* [Git](https://git-scm.com/) instalado.
* [Docker Desktop](https://www.docker.com/products/docker-desktop/) (o Docker Engine + Docker Compose) en ejecución.

### Pasos de Instalación y Despliegue

1. **Clonar el repositorio:**
   ```bash
   git clone [https://github.com/Juanlopezpablo/ClearBid-NJ.git](https://github.com/Juanlopezpablo/ClearBid-NJ.git)
   cd ClearBid-NJ