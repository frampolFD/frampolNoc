async function loadExplorer() {
  const container = document.getElementById("explorer-tree");
  if (!container) return;
  try {
    const tree = await api("/api/explorer");
    container.innerHTML = "";
    if (tree.length === 0) {
      container.innerHTML = '<div class="empty-state">No customers yet.</div>';
      return;
    }
    tree.forEach((customer) => container.appendChild(renderCustomer(customer)));
  } catch (e) {
    container.innerHTML = '<div class="empty-state">Failed to load: ' + e.message + "</div>";
  }
}

function makeNode(labelHtml, childrenEl, onClick) {
  const wrapper = document.createElement("div");
  wrapper.className = "tree-node";

  const row = document.createElement("div");
  row.className = "tree-row";

  const toggle = document.createElement("span");
  toggle.className = "toggle";
  toggle.textContent = childrenEl ? "▶" : "";
  row.appendChild(toggle);

  const label = document.createElement("span");
  label.innerHTML = labelHtml;
  row.appendChild(label);

  wrapper.appendChild(row);

  if (childrenEl) {
    childrenEl.className += " tree-children";
    wrapper.appendChild(childrenEl);
    toggle.addEventListener("click", (ev) => {
      ev.stopPropagation();
      childrenEl.classList.toggle("open");
      toggle.textContent = childrenEl.classList.contains("open") ? "▼" : "▶";
    });
  }

  row.addEventListener("click", () => {
    if (onClick) {
      onClick();
    } else if (childrenEl) {
      childrenEl.classList.toggle("open");
      toggle.textContent = childrenEl.classList.contains("open") ? "▼" : "▶";
    }
  });

  return wrapper;
}

function renderCustomer(customer) {
  const children = document.createElement("div");
  customer.cities.forEach((city) => children.appendChild(renderCity(city)));
  return makeNode('<span class="tree-label customer">' + escapeHtml(customer.name) + "</span>", children);
}

function renderCity(city) {
  const children = document.createElement("div");
  city.suburbs.forEach((suburb) => children.appendChild(renderSuburb(suburb)));
  city.branches.forEach((branch) => children.appendChild(renderBranch(branch)));
  return makeNode('<span class="tree-label">' + escapeHtml(city.name) + "</span>", children);
}

function renderSuburb(suburb) {
  const children = document.createElement("div");
  suburb.branches.forEach((branch) => children.appendChild(renderBranch(branch)));
  return makeNode('<span class="tree-label">' + escapeHtml(suburb.name) + "</span>", children);
}

function renderBranch(branch) {
  const children = document.createElement("div");
  branch.wan_links.forEach((wan) => children.appendChild(renderWan(wan)));
  const node = makeNode('<span class="tree-label">🏢 ' + escapeHtml(branch.name) + "</span>", children, () => {
    window.location.href = "/branches/" + branch.id;
  });
  return node;
}

function renderWan(wan) {
  return makeNode('<span class="tree-label wan">' + escapeHtml(wan.name) + "</span>", null, () => {
    window.location.href = "/wan-links/" + wan.id;
  });
}

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

document.addEventListener("DOMContentLoaded", loadExplorer);
