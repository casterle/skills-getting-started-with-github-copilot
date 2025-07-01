document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");

  // Helper: Sanitize text for HTML
  function sanitize(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // Function to fetch activities from API
  async function fetchActivities() {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 7000); // 7s timeout
      const response = await fetch("/activities", { signal: controller.signal });
      clearTimeout(timeout);
      const activities = await response.json();

      // Clear loading message and dropdown options
      activitiesList.innerHTML = "";
      activitySelect.innerHTML = '<option value="">-- Select an activity --</option>';

      // Populate activities list
      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const spotsLeft = details.max_participants - details.participants.length;

        // Build participants list HTML with unregister button
        let participantsHTML = "";
        if (details.participants.length > 0) {
          participantsHTML = `
            <div class="participants-section">
              <strong>Participants:</strong>
              <ul class="participants-list">
                ${details.participants.map(email => `
                  <li>
                    ${sanitize(email)}
                    <button class="unregister-btn" data-activity="${sanitize(name)}" data-email="${sanitize(email)}" title="Unregister ${sanitize(email)}">Unregister</button>
                  </li>
                `).join("")}
              </ul>
            </div>
          `;
        } else {
          participantsHTML = `
            <div class="participants-section no-participants">
              <em>No participants yet.</em>
            </div>
          `;
        }

        activityCard.innerHTML = `
          <h4>${sanitize(name)}</h4>
          <p>${sanitize(details.description)}</p>
          <p><strong>Schedule:</strong> ${sanitize(details.schedule)}</p>
          <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
          ${participantsHTML}
        `;

        activitiesList.appendChild(activityCard);

        // Add option to select dropdown
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });
    } catch (error) {
      if (error.name === 'AbortError') {
        activitiesList.innerHTML = "<p>Request timed out. Please check your connection and try again.</p>";
      } else if (!navigator.onLine) {
        activitiesList.innerHTML = "<p>You appear to be offline. Please check your internet connection.</p>";
      } else {
        activitiesList.innerHTML = "<p>Failed to load activities. Please try again later.</p>";
        console.error("Error fetching activities:", error);
      }
    }
  }

  // Helper: Set ARIA live for message
  function showMessage(text, type = "info") {
    messageDiv.textContent = text;
    messageDiv.className = type;
    messageDiv.setAttribute("role", "alert");
    messageDiv.setAttribute("aria-live", "assertive");
    messageDiv.classList.remove("hidden");
    setTimeout(() => {
      messageDiv.classList.add("hidden");
    }, 5000);
  }

  // Handle form submission
  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("email").value;
    const activity = document.getElementById("activity").value;

    // Client-side input sanitization (basic)
    if (!email || !activity) {
      showMessage("Please fill out all fields.", "error");
      return;
    }
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
      showMessage("Please enter a valid email address.", "error");
      return;
    }

    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 7000); // 7s timeout
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/signup?email=${encodeURIComponent(email)}`,
        {
          method: "POST",
          signal: controller.signal
        }
      );
      clearTimeout(timeout);

      const result = await response.json();
      const errorType = response.headers.get("X-Error-Type");

      if (response.ok) {
        showMessage(result.message, "success");
        signupForm.reset();
      } else if (response.status === 409) {
        // Handle specific 409 errors
        if (errorType === "activity_full") {
          showMessage("This activity is full. Please choose another.", "error");
        } else if (errorType === "already_registered") {
          showMessage("You are already registered for this activity.", "error");
        } else {
          showMessage(result.detail || "A conflict occurred.", "error");
        }
      } else if (response.status === 422) {
        showMessage(result.detail || "Invalid input.", "error");
      } else if (response.status === 429) {
        showMessage(result.detail || "Too many requests. Please try again later.", "error");
      } else {
        showMessage(result.detail || "An error occurred", "error");
      }
    } catch (error) {
      if (error.name === 'AbortError') {
        showMessage("Request timed out. Please check your connection and try again.", "error");
      } else if (!navigator.onLine) {
        showMessage("You appear to be offline. Please check your internet connection.", "error");
      } else {
        showMessage("Failed to sign up. Please try again.", "error");
        console.error("Error signing up:", error);
      }
    }
  });

  // Initialize app
  fetchActivities();
});
