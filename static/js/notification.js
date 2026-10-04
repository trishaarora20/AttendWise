document.addEventListener("DOMContentLoaded", async () => {
    const enableButton = document.getElementById("enableNotifications");
    const disableButton = document.getElementById("disableNotifications");
    const testButton = document.getElementById("testNotification");
    const reminderSelect = document.getElementById("reminderMinutes");
    const statusText = document.getElementById("notificationStatus");

    let registration = null;

    // Check browser support
    if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
        if (statusText) {
            statusText.textContent =
                "Push notifications are not supported by this browser.";
        }

        if (enableButton) enableButton.disabled = true;
        return;
    }

    // Register the service worker
    try {
        registration = await navigator.serviceWorker.register("/static/sw.js");

        console.log("Service Worker registered:", registration);

        await navigator.serviceWorker.ready;

        updateNotificationStatus();
    } catch (error) {
        console.error("Service Worker registration failed:", error);

        if (statusText) {
            statusText.textContent =
                "Could not start notification service.";
        }
    }

    // Ask for notification permission and subscribe
    if (enableButton) {
        enableButton.addEventListener("click", async () => {
            try {
                const permission = await Notification.requestPermission();

                if (permission !== "granted") {
                    alert(
                        "Notification permission was not granted. Please allow notifications in your browser settings."
                    );
                    return;
                }

                const publicKeyResponse = await fetch(
                    "/notifications/vapid-public-key"
                );

                if (!publicKeyResponse.ok) {
                    throw new Error("Could not get VAPID public key.");
                }

                const publicKeyData = await publicKeyResponse.json();

                const publicKey = publicKeyData.publicKey;

                if (!publicKey) {
                    throw new Error("VAPID public key is missing.");
                }

                const readyRegistration =
                    await navigator.serviceWorker.ready;

                let subscription =
                    await readyRegistration.pushManager.getSubscription();

                // Create a new subscription if one doesn't exist
                if (!subscription) {
                    subscription =
                        await readyRegistration.pushManager.subscribe({
                            userVisibleOnly: true,
                            applicationServerKey: urlBase64ToUint8Array(
                                publicKey
                            ),
                        });
                }

                // Send subscription to Flask
                const response = await fetch(
                    "/notifications/subscribe",
                    {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                        },
                        body: JSON.stringify({
                            subscription: subscription.toJSON(),
                            reminder_minutes: parseInt(
                                reminderSelect?.value || "10"
                            ),
                        }),
                    }
                );

                const result = await response.json();

                if (!response.ok) {
                    throw new Error(
                        result.error || "Could not save notification settings."
                    );
                }

                if (statusText) {
                    statusText.textContent =
                        "🔔 Notifications are enabled!";
                }

                alert("Notifications enabled successfully! 🔔");

                updateNotificationStatus();
            } catch (error) {
                console.error("Notification setup error:", error);

                alert(
                    "Could not enable notifications: " +
                        error.message
                );
            }
        });
    }

    // Disable notifications
    if (disableButton) {
        disableButton.addEventListener("click", async () => {
            try {
                const readyRegistration =
                    await navigator.serviceWorker.ready;

                const subscription =
                    await readyRegistration.pushManager.getSubscription();

                if (subscription) {
                    await subscription.unsubscribe();
                }

                const response = await fetch(
                    "/notifications/disable",
                    {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                        },
                    }
                );

                const result = await response.json();

                if (!response.ok) {
                    throw new Error(
                        result.error || "Could not disable notifications."
                    );
                }

                if (statusText) {
                    statusText.textContent =
                        "Notifications are disabled.";
                }

                alert("Notifications disabled.");

                updateNotificationStatus();
            } catch (error) {
                console.error(
                    "Notification disable error:",
                    error
                );

                alert(
                    "Could not disable notifications: " +
                        error.message
                );
            }
        });
    }

    // Change reminder time
    if (reminderSelect) {
        reminderSelect.addEventListener("change", async () => {
            const value = parseInt(reminderSelect.value);

            if (![5, 10, 15].includes(value)) {
                return;
            }

            try {
                const response = await fetch(
                    "/notifications/settings",
                    {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                        },
                        body: JSON.stringify({
                            reminder_minutes: value,
                        }),
                    }
                );

                const result = await response.json();

                if (!response.ok) {
                    throw new Error(
                        result.error ||
                            "Could not update reminder setting."
                    );
                }

                if (statusText) {
                    statusText.textContent =
                        `Reminder time set to ${value} minutes.`;
                }

                console.log(
                    "Reminder updated:",
                    value,
                    "minutes"
                );
            } catch (error) {
                console.error(
                    "Reminder setting error:",
                    error
                );

                alert(
                    "Could not update reminder time: " +
                        error.message
                );
            }
        });
    }

    // Test notification
    if (testButton) {
        testButton.addEventListener("click", async () => {
            try {
                const response = await fetch(
                    "/notifications/test",
                    {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                        },
                    }
                );

                const result = await response.json();

                if (!response.ok) {
                    throw new Error(
                        result.error ||
                            "Could not send test notification."
                    );
                }

                alert(
                    "Test notification sent! 🔔 Check your device."
                );
            } catch (error) {
                console.error(
                    "Test notification error:",
                    error
                );

                alert(
                    "Could not send test notification: " +
                        error.message
                );
            }
        });
    }

    // Update UI based on current permission/subscription
    async function updateNotificationStatus() {
        if (!statusText) return;

        if (!("Notification" in window)) {
            statusText.textContent =
                "Notifications are not supported.";
            return;
        }

        if (Notification.permission === "denied") {
            statusText.textContent =
                "Notifications are blocked in your browser.";
            return;
        }

        try {
            const readyRegistration =
                await navigator.serviceWorker.ready;

            const subscription =
                await readyRegistration.pushManager.getSubscription();

            if (subscription && Notification.permission === "granted") {
                statusText.textContent =
                    "🔔 Notifications are enabled.";
            } else {
                statusText.textContent =
                    "Notifications are not enabled yet.";
            }
        } catch (error) {
            console.error(
                "Could not check notification status:",
                error
            );
        }
    }

    // Convert VAPID Base64 URL key to Uint8Array
    function urlBase64ToUint8Array(base64String) {
        const padding = "=".repeat(
            (4 - (base64String.length % 4)) % 4
        );

        const base64 = (
            base64String +
            padding
        )
            .replace(/-/g, "+")
            .replace(/_/g, "/");

        const rawData = window.atob(base64);

        const outputArray = new Uint8Array(
            rawData.length
        );

        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }

        return outputArray;
    }
});