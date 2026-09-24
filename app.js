let activeRecipeId = null;

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
  checkStatus();
  loadRecipes();

  // Search filter listener with short debounce
  let debounceTimer;
  document.getElementById("searchInput").addEventListener("input", () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(loadRecipes, 300);
  });

  // Category filter listener
  document.getElementById("categorySelect").addEventListener("change", loadRecipes);

  // Toggle ingredient form
  document.getElementById("toggleIngBtn").addEventListener("click", () => {
    document.getElementById("ingFormBox").classList.toggle("d-none");
  });

  // Delete recipe from modal
  document.getElementById("deleteRecipeBtn").addEventListener("click", () => {
    if (activeRecipeId) deleteRecipe(activeRecipeId);
  });
});

// Check if backend service is reachable
async function checkStatus() {
  const el = document.getElementById("serviceStatus");
  try {
    const res = await fetch("/health");
    el.innerHTML = res.ok 
      ? '<span class="status-dot"></span>Service: Online' 
      : '<span class="status-dot down"></span>Service: Degraded';
  } catch {
    el.innerHTML = '<span class="status-dot down"></span>Service: Offline';
  }
}

// Fetch recipes from REST API
async function loadRecipes() {
  const search = document.getElementById("searchInput").value.trim();
  const category = document.getElementById("categorySelect").value;
  const container = document.getElementById("recipeContainer");

  let url = `/api/recipes?limit=50`;
  if (search) url += `&search=${encodeURIComponent(search)}`;
  if (category) url += `&category=${encodeURIComponent(category)}`;

  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error("Could not fetch recipes");
    const data = await res.json();
    renderCards(data.recipes || []);
  } catch (err) {
    container.innerHTML = `
      <div class="col-12 text-center py-4 text-danger">
        <i class="fa-solid fa-circle-exclamation me-1"></i> Failed to load recipes.
      </div>`;
  }
}

// Render recipe cards into the grid
function renderCards(recipes) {
  const container = document.getElementById("recipeContainer");
  if (recipes.length === 0) {
    container.innerHTML = `<div class="col-12 text-center py-5 text-muted">No recipes found.</div>`;
    return;
  }

  container.innerHTML = recipes.map(r => `
    <div class="col-md-6 col-lg-4">
      <div class="recipe-card p-3 h-100 d-flex flex-column" onclick="openRecipe(${r.id})">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <span class="badge-cat small">${escapeHtml(r.category)}</span>
          <span class="text-muted small"><i class="fa-regular fa-clock me-1"></i>${r.prep_time + r.cook_time}m</span>
        </div>
        <h6 class="fw-bold mb-1">${escapeHtml(r.name)}</h6>
        <p class="text-muted small flex-grow-1 mb-3">${escapeHtml(r.description || 'No description.')}</p>
        <div class="d-flex justify-content-between align-items-center border-top pt-2 small text-muted">
          <span><i class="fa-solid fa-user-group me-1"></i>${r.servings} servings</span>
          <span class="text-primary fw-medium">View &rarr;</span>
        </div>
      </div>
    </div>
  `).join("");
}

// Clean up leftover modal backdrops
function resetModalBackdrop() {
  document.querySelectorAll(".modal-backdrop").forEach(el => el.remove());
  document.body.classList.remove("modal-open");
  document.body.style.overflow = "";
}

// Open recipe details modal
async function openRecipe(id) {
  activeRecipeId = id;
  resetModalBackdrop();

  const modalEl = document.getElementById("detailsModal");
  let modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
  modalEl.addEventListener("hidden.bs.modal", resetModalBackdrop, { once: true });

  try {
    const res = await fetch(`/api/recipes/${id}`);
    if (!res.ok) throw new Error("Could not load details");
    const r = await res.json();

    document.getElementById("detailName").textContent = r.name;
    document.getElementById("detailCategory").textContent = r.category;
    document.getElementById("detailDesc").textContent = r.description || "";
    document.getElementById("detailPrep").textContent = r.prep_time;
    document.getElementById("detailCook").textContent = r.cook_time;
    document.getElementById("detailServings").textContent = r.servings;
    document.getElementById("detailInstructions").textContent = r.instructions;

    // Render ingredients list
    const list = document.getElementById("ingredientList");
    if (!r.ingredients || r.ingredients.length === 0) {
      list.innerHTML = `<li class="list-group-item text-muted text-center py-2 small">No ingredients added yet.</li>`;
    } else {
      list.innerHTML = r.ingredients.map(ing => `
        <li class="list-group-item d-flex justify-content-between align-items-center py-2">
          <span>${escapeHtml(ing.name)}</span>
          <div>
            <span class="badge bg-light text-dark border me-2">${ing.quantity} ${escapeHtml(ing.unit)}</span>
            <button class="btn btn-link btn-sm text-danger p-0" onclick="deleteIngredient(${ing.id}, event)">
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>
        </li>
      `).join("");
    }

    modal.show();
  } catch (err) {
    alert("Error: " + err.message);
  }
}

// Save a new recipe
async function handleCreateRecipe(e) {
  e.preventDefault();

  const recipeData = {
    name: document.getElementById("newName").value.trim(),
    category: document.getElementById("newCategory").value,
    prep_time: parseInt(document.getElementById("newPrep").value) || 0,
    cook_time: parseInt(document.getElementById("newCook").value) || 0,
    servings: parseInt(document.getElementById("newServings").value) || 1,
    description: document.getElementById("newDesc").value.trim(),
    instructions: document.getElementById("newInstructions").value.trim()
  };

  try {
    const res = await fetch("/api/recipes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(recipeData)
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error || "Save failed");
    }

    const modal = bootstrap.Modal.getInstance(document.getElementById("createModal"));
    if (modal) modal.hide();
    document.getElementById("recipeForm").reset();
    loadRecipes();
  } catch (err) {
    alert("Error creating recipe: " + err.message);
  }
}

// Save ingredient for active recipe
async function saveIngredient() {
  if (!activeRecipeId) return;

  const name = document.getElementById("ingName").value.trim();
  const quantity = parseFloat(document.getElementById("ingQty").value);
  const unit = document.getElementById("ingUnit").value.trim();

  if (!name || isNaN(quantity) || !unit) {
    alert("Please fill in ingredient name, quantity, and unit.");
    return;
  }

  try {
    const res = await fetch("/api/ingredients", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ recipe_id: activeRecipeId, name, quantity, unit })
    });

    if (!res.ok) throw new Error("Failed to add ingredient");

    document.getElementById("ingName").value = "";
    document.getElementById("ingQty").value = "";
    document.getElementById("ingUnit").value = "";
    document.getElementById("ingFormBox").classList.add("d-none");

    openRecipe(activeRecipeId);
  } catch (err) {
    alert("Error: " + err.message);
  }
}

// Delete ingredient
async function deleteIngredient(id, evt) {
  if (evt) evt.stopPropagation();
  if (!confirm("Delete this ingredient?")) return;

  try {
    const res = await fetch(`/api/ingredients/${id}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Delete failed");
    openRecipe(activeRecipeId);
  } catch (err) {
    alert("Error: " + err.message);
  }
}

// Delete recipe
async function deleteRecipe(id) {
  if (!confirm("Are you sure you want to delete this recipe?")) return;

  try {
    const res = await fetch(`/api/recipes/${id}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Delete failed");

    const modal = bootstrap.Modal.getInstance(document.getElementById("detailsModal"));
    if (modal) modal.hide();
    loadRecipes();
  } catch (err) {
    alert("Error: " + err.message);
  }
}

// Sanitize string output
function escapeHtml(str) {
  if (!str) return "";
  const d = document.createElement("div");
  d.innerText = str;
  return d.innerHTML;
}
