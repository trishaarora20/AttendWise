self.addEventListener("push", function (event) {
    let data = {
        title: "AttendWise 🔔",
        body: "You have an upcoming class.",
        url: "/attendance"
    };

    if (event.data) {
        try {
            data = event.data.json();
        } catch (error) {
            console.error("Could not read push data:", error);
        }
    }

    const options = {
        body: data.body,
        icon: "/static/icon-192.png",
        badge: "/static/icon-192.png",
        data: {
            url: data.url || "/attendance"
        },
        requireInteraction: true
    };

    event.waitUntil(
        self.registration.showNotification(
            data.title || "AttendWise 🔔",
            options
        )
    );
});


self.addEventListener("notificationclick", function (event) {
    event.notification.close();

    const url =
        event.notification.data?.url || "/attendance";

    event.waitUntil(
        clients.matchAll({
            type: "window",
            includeUncontrolled: true
        }).then(function (clientList) {

            for (const client of clientList) {
                if ("focus" in client) {
                    client.navigate(url);
                    return client.focus();
                }
            }

            if (clients.openWindow) {
                return clients.openWindow(url);
            }
        })
    );
});