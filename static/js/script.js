
// ===================================
// PHASE 2 - SMART NOTES JAVASCRIPT
// ===================================


// DELETE CONFIRMATION

function confirmDelete() {

    return confirm(
        "Are you sure you want to delete this note?"
    );

}


// ===================================
// BROWSER NOTIFICATION PERMISSION
// ===================================

document.addEventListener("DOMContentLoaded", function () {

    const enableButton = document.getElementById(
        "enableNotifications"
    );

    if (enableButton) {

        enableButton.addEventListener("click", async function () {

            if (!("Notification" in window)) {

                alert("Your browser does not support notifications.");
                return;

            }

            const permission = await Notification.requestPermission();

            if (permission === "granted") {

                alert("Reminder notifications enabled!");

                checkReminders();

            } else {

                alert("Please allow notifications in your browser settings.");

            }

        });

    }


    // CHECK REMINDERS EVERY 30 SECONDS

    checkReminders();

    setInterval(checkReminders, 30000);


    // SEARCH INPUT

    const searchInput = document.querySelector(
        '.advanced-search input[name="search"]'
    );

    if (searchInput) {

        searchInput.addEventListener("keydown", function (event) {

            if (event.key === "Enter") {

                event.preventDefault();

                searchInput.closest("form").submit();

            }

        });

    }

});


// ===================================
// REMINDER CHECKING
// ===================================

function checkReminders() {

    if (!("Notification" in window)) {
        return;
    }

    if (Notification.permission !== "granted") {
        return;
    }

    const currentTime = new Date();

    const notes = document.querySelectorAll(
        ".note-card[data-reminder]"
    );

    notes.forEach(function (note) {

        const reminder = note.dataset.reminder;

        if (!reminder) {
            return;
        }

        const reminderTime = new Date(reminder);

        const noteId = note.dataset.noteId;

        const notificationKey = "reminder-" + noteId;

        if (
            !Number.isNaN(reminderTime.getTime()) &&
            reminderTime <= currentTime &&
            !sessionStorage.getItem(notificationKey)
        ) {

            const title = note.querySelector("h3");

            new Notification("Smart Notes Reminder", {

                body: "Reminder: " +
                    (title ? title.textContent.trim() : "Your saved note"),

                icon: ""

            });

            sessionStorage.setItem(notificationKey, "shown");

        }

    });

}
