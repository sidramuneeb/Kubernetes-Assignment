# Recipe Collection Management System

A cloud-native microservices application built with Python (Flask), PostgreSQL 15, Docker, and Kubernetes. The system provides a web dashboard and REST APIs for managing recipes and ingredients across independently scalable services.

## System Architecture

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
               |                                                   |
               v (Direct handling)                                 v (Proxy Forwarding)
+-----------------------------+                     +-----------------------------+
|       recipes-service       |                     |     ingredients-service     |
|   (Python 3.11 / Flask)     |                     |   (Python 3.11 / Flask)     |
|   Port: 5001                |                     |   Port: 5002                |
|   Replicas: 2 to 5 (HPA)    |<------------------->|   Replicas: 2 to 5 (HPA)    |
|   - Serves Web Dashboard    |  Inter-Service REST |   - Manages Ingredients     |
|   - Recipe CRUD Operations  |      Calls (HTTP)   |   - Validates Recipe IDs    |
|   - Aggregates Ingredients  |                     |   - Bulk Cascade Deletion   |
+--------------+--------------+                     +--------------+--------------+
               |                                                   |
               | SQLAlchemy                                        | SQLAlchemy
               v                                                   v
+---------------------------------------------------------------------------------+
|                               PostgreSQL 15 Server                              |
|                          (Service: postgres-service:5432)                       |
|                                                                                 |
|   [ Database: recipes_db ]                           [ Database: ingredients_db ]|
|   - recipes table                                    - ingredients table        |
|                                                                                 |
|                   PersistentVolumeClaim: 1Gi Storage                            |
+---------------------------------------------------------------------------------+
```

## Microservices Breakdown

### 1. Recipes Service (`recipes-service`)
* Port: 5001
* Database: `recipes_db`
* Roles: Manages recipe CRUD operations, category filtering, search, and serves the browser UI dashboard.
* Inter-service communication: Queries the Ingredients service to embed ingredient data when retrieving a single recipe, and proxies ingredient requests from the web UI.

### 2. Ingredients Service (`ingredients-service`)
* Port: 5002
* Database: `ingredients_db`
* Roles: Manages ingredient CRUD operations linked by `recipe_id`.
* Inter-service validation: Validates that a recipe exists by calling the Recipes service before allowing an ingredient to be saved.

### 3. PostgreSQL Database (`postgres-service`)
* Port: 5432 (Internal ClusterIP)
* Storage: 1Gi PersistentVolume
* Contains two isolated databases (`recipes_db` and `ingredients_db`), enforcing the database-per-service pattern.

## Quick Reference: Deployment & Management Commands

### 1. Deploy the Application
```powershell
# Step 1: Enable Metrics Server (required for HPA autoscaling)
kubectl apply -f kubernetes/metrics-server.yaml

# Step 2: Deploy all application services (uses Kustomize to inject database/init.sql dynamically)
kubectl apply -k .
```

### 2. Check Application Resources
View basic resources in the `recipe-app` namespace:
```powershell
kubectl get all -n recipe-app
```

View all cluster resources (including storage PVCs, autoscalers HPA, and Ingress):
```powershell
kubectl get all,pvc,hpa,ingress -n recipe-app
```

### 3. Useful Monitoring Commands
Watch pods starting up and changing in real-time:
```powershell
kubectl get pods -n recipe-app -w
```

View live CPU & Memory usage per pod:
```powershell
kubectl top pods -n recipe-app
```

View logs for Recipes Service:
```powershell
kubectl logs -l app=recipes-service -n recipe-app --tail=50
```

View logs for Ingredients Service:
```powershell
kubectl logs -l app=ingredients-service -n recipe-app --tail=50
```

View logs for PostgreSQL Database:
```powershell
kubectl logs -l app=postgres -n recipe-app --tail=50
```

### 4. Stop / Clean Up All Resources
```powershell
kubectl delete -k .
```

## Accessing the Application

Once all pods show `1/1 Running`, open your web browser and navigate to:
* **Web Dashboard**: http://localhost:5001/
* **Recipes Swagger API Docs**: http://localhost:5001/apidocs/
* **Ingredients Swagger API Docs**: http://localhost:5002/apidocs/

## REST API Reference

### Recipes Service (Port 5001)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Health probe checking database connectivity |
| `GET` | `/api/recipes` | List all recipes (supports `?search=` and `?category=`) |
| `GET` | `/api/recipes/<id>` | Get single recipe with ingredients aggregated |
| `POST` | `/api/recipes` | Create a new recipe |
| `PUT` | `/api/recipes/<id>` | Update an existing recipe |
| `DELETE` | `/api/recipes/<id>` | Delete recipe and cascade delete ingredients |
| `GET` | `/api/recipes/category/<name>` | Filter recipes by category |

### Ingredients Service (Port 5002)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Health probe checking database connectivity |
| `GET` | `/api/ingredients` | List ingredients (supports `?recipe_id=`) |
| `GET` | `/api/ingredients/<id>` | Get single ingredient details |
| `POST` | `/api/ingredients` | Create ingredient (validates recipe existence first) |
| `PUT` | `/api/ingredients/<id>` | Update an existing ingredient |
| `DELETE` | `/api/ingredients/<id>` | Delete an ingredient |
| `DELETE` | `/api/ingredients/by-recipe/<id>` | Bulk delete ingredients for a recipe |

## Scaling Microservices

### Manual Scaling
Scale the Recipes service up to 5 replicas:

```powershell
kubectl scale deployment recipes-deployment --replicas=5 -n recipe-app
kubectl get pods -n recipe-app -l app=recipes-service
```

Scale back to 2 replicas:

```powershell
kubectl scale deployment recipes-deployment --replicas=2 -n recipe-app
```

### Horizontal Pod Autoscaling (HPA)
Both services have HPAs configured (`min: 2`, `max: 5`, target CPU: 80%). To inspect active autoscalers:

```powershell
kubectl get hpa -n recipe-app
```

---

## How to Test Horizontal Pod Autoscaling (HPA)

To test that Kubernetes automatically scales up pod replicas under heavy traffic:

### Step 1: Open a terminal to watch pods scaling in real-time
In your first terminal, run:
```powershell
kubectl get pods -n recipe-app -w
```


### Step 2: Generate load on BOTH microservices
In a second terminal, launch the load generator container that continuously stresses both `recipes-service` and `ingredients-service`:
```powershell
kubectl run load-generator --rm -i --tty --image=busybox:1.28 -n recipe-app -- /bin/sh -c "while true; do wget -q -O- http://recipes-service:5001/api/recipes/1; wget -q -O- http://ingredients-service:5002/api/ingredients; done"
```

> **Why this tests both services:** Calling `http://recipes-service:5001/api/recipes/1` forces the Recipes service to query the Ingredients service over HTTP to fetch recipe ingredients, while the second `wget` directly queries the Ingredients service.

### Step 3: Observe automatic scale-up
Within 1–2 minutes, as CPU usage crosses the 80% threshold, the HPA will automatically increase the replica count from **2** up to **3, 4, or 5 pods** for both services!

### Step 4: Stop the load and observe scale-down
Press `Ctrl + C` in the load generator terminal. Once traffic stops and CPU usage drops back down, Kubernetes will automatically scale the pods back down to the minimum of **2** replicas.

---

## Building and Pushing Docker Images

If you make code changes and need to rebuild and push updated Docker images to Docker Hub:

### 1. Log in to Docker Hub
```bash
docker login
```

### 2. Build the Docker Images
```bash
# Build Recipes Service
docker build -t sidra1634/recipes-service:latest ./recipes-service

# Build Ingredients Service
docker build -t sidra1634/ingredients-service:latest ./ingredients-service
```

### 3. Push to Docker Hub
```bash
# Push Recipes Service
docker push sidra1634/recipes-service:latest

# Push Ingredients Service
docker push sidra1634/ingredients-service:latest
```

