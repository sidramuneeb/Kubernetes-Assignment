# Recipe Collection Management System - Assignment Report

## 1. Description of the Software Built and What It Does

The Recipe Collection Management System is a web-based app built using microservices for managing cooking recipes and ingredients. It runs in Docker containers on Kubernetes and provides an interactive web dashboard alongside RESTful APIs.

Main features:
* **Browse & Search Recipes**: View recipes categorized by cuisine (Italian, Mexican, Asian, Mediterranean, Dessert) and search by keyword.
* **View Recipe Details**: Inspect preparation times, cooking times, serving sizes, and step-by-step instructions.
* **Ingredient Breakdown**: Automatically fetch and manage ingredient details (quantity, unit) linked to specific recipes via inter-service REST calls.
* **Full CRUD Operations**: Create, view, update, and delete recipes and ingredients directly from the browser UI.
* **Interactive API Documentation**: Test all REST endpoints using built-in Swagger UI at `/apidocs/`.

The system consists of two Python/Flask backend microservices and a PostgreSQL database.

---

## 2. Software Architecture Design

### System Overview Diagram

```
                     +---------------------------------------+
                     |              Web Browser              |
                     |         http://localhost:5001         |
                     +-------------------+-------------------+
                                         |
                                         | HTTP Port 5001
                                         v
                     +---------------------------------------+
                     |    Kubernetes LoadBalancer Service    |
                     |           (recipes-service)           |
                     +-------------------+-------------------+
                                         |
               +-------------------------+-------------------------+
               | (Direct Handling)                                 | (Internal HTTP Proxy)
               v                                                   v
+-----------------------------+                     +-----------------------------+
|       recipes-service       |                     |     ingredients-service     |
|   (Python 3.11 / Flask)     |                     |   (Python 3.11 / Flask)     |
|   Replicas: 2 to 5 (HPA)    |<------------------->|   Replicas: 2 to 5 (HPA)    |
|   Port: 5001                |  Inter-Service REST |   Port: 5002                |
|   - Serves Web Dashboard    |      Calls          |   - Manages Ingredients     |
|   - Recipe CRUD Operations  |                     |   - Validates Recipe IDs    |
|   - Aggregates Ingredients  |                     |   - Bulk Cascade Deletion   |
+--------------+--------------+                     +--------------+--------------+
               |                                                   |
               | SQLAlchemy                                        | SQLAlchemy
               v                                                   v
+---------------------------------------------------------------------------------+
|                               PostgreSQL 15 Server                              |
|                          (Service: postgres-service:5432)                       |
|                                                                                 |
|   [ Database: recipes_db ]                          [ Database: ingredients_db ]|
|   - recipes table                                    - ingredients table        |
|                                                                                 |
|                   PersistentVolumeClaim: 1Gi Storage                            |
+---------------------------------------------------------------------------------+
```

### Component Roles and Responsibilities

* **Web Browser UI**: Renders the frontend user interface using HTML, CSS, and JavaScript. Communicates directly with `recipes-service` on port 5001.
* **Recipes Microservice (`recipes-service`)**: Manages recipe records (CRUD operations, search, category filtering). Hosts the frontend dashboard and proxies ingredient requests internally to `ingredients-service`. When a user requests recipe details, it queries `ingredients-service` over HTTP to attach the ingredients list.
* **Ingredients Microservice (`ingredients-service`)**: Handles ingredient data. Before saving a new ingredient, it makes an HTTP call back to `recipes-service` to confirm the recipe ID exists. It also handles bulk cleanup when a recipe is deleted.
* **PostgreSQL Database (`postgres-service`)**: Holds two separate databases (`recipes_db` and `ingredients_db`) on PostgreSQL 15, backed by a 1Gi Kubernetes PersistentVolume.
* **Kubernetes Layer**: Handles container deployment, service discovery, networking, and automatic pod scaling based on CPU usage.

### Cloud Architecture Patterns Used

* **Database-per-Service**: Each microservice strictly owns its own database (`recipes_db` and `ingredients_db`), preventing direct cross-database reads or writes.
* **Backend-For-Frontend (BFF) / API Gateway Proxy**: `recipes-service` serves the UI and forwards ingredient API traffic internally, keeping the internal Kubernetes setup hidden from the browser.
* **Service Discovery**: Microservices find each other using internal Kubernetes DNS names (`http://recipes-service:5001`, `http://ingredients-service:5002`, `postgres-service:5432`) instead of hardcoded IPs.
* **Health Monitoring**: Both services expose `/health` endpoints for Kubernetes readiness and liveness probes.
* **Elastic Horizontal Autoscaling**: Kubernetes HPAs automatically adjust pod counts between 2 and 5 instances based on CPU demand.
* **Infrastructure as Code (IaC)**: All infrastructure is defined declaratively using YAML manifests in the `kubernetes/` folder.

### Mapping of Software Components to Microservices

| Component | Microservice / Resource | File Location |
| :--- | :--- | :--- |
| Recipe Model & Storage | `recipes-service` | `recipes-service/models.py` |
| Recipe REST Endpoints & Web UI | `recipes-service` | `recipes-service/app.py` |
| Ingredient Model & Storage | `ingredients-service` | `ingredients-service/models.py` |
| Ingredient REST Endpoints | `ingredients-service` | `ingredients-service/app.py` |
| Recipe ID Validation Call | `ingredients-service` | `ingredients-service/app.py` |
| Database Schema & Seed Data | PostgreSQL / Kustomize | `database/init.sql` (injected via `kubernetes/kustomization.yaml`) |
| External HTTP Entrypoint (5001) | Kubernetes Service | `kubernetes/recipes-service.yaml` |
| Internal Service Access (5002) | Kubernetes Service | `kubernetes/ingredients-service.yaml` |
| Database Storage Volume | Kubernetes PV & PVC | `kubernetes/postgres-pv.yaml`, `postgres-pvc.yaml` |
| Auto-scaling Setup | Kubernetes HPA | `kubernetes/recipes-hpa.yaml`, `ingredients-hpa.yaml` |
| Application Config & Secrets | Kubernetes ConfigMap / Secret | `kubernetes/configmap.yaml`, `kubernetes/secrets.yaml` |

---

## 3. Benefits, Challenges, and Security Discussion

### Benefits of the Architecture

* **Independent Scaling**: Read traffic for searching recipes is much higher than writing ingredients. `recipes-service` can scale up to 5 pods under load without needing to scale `ingredients-service`, saving compute resources.
* **Fault Isolation**: If `ingredients-service` crashes or restarts, users can still view recipes (the app gracefully returns recipes with an empty ingredient list rather than crashing).
* **Independent Deployments**: Developers can update ingredient logic without redeploying or affecting the recipes service.

### Challenges and Mitigations

1. **Inter-Service Network Latency**
   * *Challenge*: Fetching a recipe requires an HTTP network call between services instead of an in-memory SQL join.
   * *What was done*: Services communicate over the fast internal Kubernetes network with a 5-second timeout (`REQUEST_TIMEOUT=5s`) to avoid blocking.
   * *What can be done*: Add a Redis cache for popular recipes to reduce internal HTTP calls.

2. **Data Consistency Without Foreign Keys**
   * *Challenge*: Because the databases are separate, standard SQL foreign key constraints cannot span across `recipes_db` and `ingredients_db`.
   * *What was done*: `ingredients-service` makes an HTTP check to `recipes-service` before creating ingredients. Deleting a recipe sends an API request to delete linked ingredients.
   * *What can be done*: Use an event-driven message queue (e.g. RabbitMQ) for reliable background cleanup.

3. **Distributed Logging**
   * *Challenge*: Logs are split across different pods, making troubleshooting trickier.
   * *What was done*: Standardized structured logging with timestamps and HTTP status codes across all services.
   * *What can be done*: Add distributed tracing headers (`X-Correlation-ID`) across requests.

### Security Discussion

**What has been done:**
* **Secrets Management**: Database passwords are stored in Kubernetes `Secret` objects and injected into containers at runtime, keeping them out of code files and Git repositories.
* **SQL Injection Prevention**: All queries use SQLAlchemy ORM with parameterized inputs. Flask routes validate numeric IDs (`<int:recipe_id>`).
* **Container Security**: Docker containers run as a non-root system user (`appuser`).
* **Network Isolation**: PostgreSQL uses a `ClusterIP` service, so port 5432 cannot be accessed from outside the Kubernetes cluster.

**What can be done in production:**
* **TLS Encryption**: Use an Ingress controller with Let's Encrypt certificates for HTTPS.
* **Authentication**: Add JWT token authentication to protect creation, edit, and deletion endpoints (`POST`, `PUT`, `DELETE`).
* **Network Policies**: Set up Kubernetes `NetworkPolicy` rules to restrict pod-to-pod network traffic.
