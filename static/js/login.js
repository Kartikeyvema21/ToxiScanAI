fetch("/api/auth/me")
  .then((res) => res.json())
  .then((data) => {
    if (data.authenticated) window.location.href = "/dashboard";
  });

function switchTab(tab) {
  const loginForm = document.getElementById("loginForm");
  const registerForm = document.getElementById("registerForm");
  const tabs = document.querySelectorAll(".tab");

  if (tab === "login") {
    loginForm.style.display = "block";
    registerForm.style.display = "none";
    tabs[0].classList.add("active");
    tabs[1].classList.remove("active");
  } else {
    loginForm.style.display = "none";
    registerForm.style.display = "block";
    tabs[0].classList.remove("active");
    tabs[1].classList.add("active");
  }
  hideMessage();
}

function fillDemo(username, password) {
  document.getElementById("loginUsername").value = username;
  document.getElementById("loginPassword").value = password;
  handleLogin(new Event("submit"));
}

function showMessage(msg, type) {
  const msgDiv = document.getElementById("message");
  msgDiv.textContent = msg;
  msgDiv.className = `message ${type}`;
}

function hideMessage() {
  const msgDiv = document.getElementById("message");
  msgDiv.style.display = "none";
}

function setLoading(btn, loading) {
  if (loading) {
    btn.innerHTML = '<span class="loading"></span> Processing...';
    btn.disabled = true;
  } else {
    btn.innerHTML = btn.id === "loginBtn" ? "Login" : "Register";
    btn.disabled = false;
  }
}

async function handleLogin(event) {
  event.preventDefault();
  const username = document.getElementById("loginUsername").value;
  const password = document.getElementById("loginPassword").value;
  const btn = document.getElementById("loginBtn");

  if (!username || !password) {
    showMessage("Please enter username and password", "error");
    return;
  }

  setLoading(btn, true);
  hideMessage();

  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    const data = await res.json();

    if (res.ok && data.success) {
      showMessage("Login successful! Redirecting...", "success");
      setTimeout(() => (window.location.href = "/dashboard"), 1000);
    } else {
      showMessage(data.error || "Login failed", "error");
    }
  } catch (err) {
    showMessage("Connection error. Please try again.", "error");
  } finally {
    setLoading(btn, false);
  }
}

async function handleRegister(event) {
  event.preventDefault();
  const username = document.getElementById("regUsername").value;
  const email = document.getElementById("regEmail").value;
  const password = document.getElementById("regPassword").value;
  const confirm = document.getElementById("regConfirm").value;
  const btn = document.getElementById("registerBtn");

  if (password !== confirm) {
    showMessage("Passwords do not match!", "error");
    return;
  }

  if (password.length < 4) {
    showMessage("Password must be at least 4 characters", "error");
    return;
  }

  setLoading(btn, true);
  hideMessage();

  try {
    const res = await fetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password, email }),
    });

    const data = await res.json();

    if (res.ok) {
      showMessage("Registration successful! Please login.", "success");
      setTimeout(() => {
        switchTab("login");
        document.getElementById("loginUsername").value = username;
      }, 1500);
    } else {
      showMessage(data.error || "Registration failed", "error");
    }
  } catch (err) {
    showMessage("Connection error. Please try again.", "error");
  } finally {
    setLoading(btn, false);
  }
}

document.getElementById("password")?.addEventListener("keypress", (e) => {
  if (e.key === "Enter") handleLogin(e);
});
