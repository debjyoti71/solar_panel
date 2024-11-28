let map;
let marker;

// Initialize Google Map
function initMap() {
    map = new google.maps.Map(document.getElementById("map"), {
        center: { lat: 22.737195, lng: 88.190791 }, // Default view (India)
        zoom: 5,
    });

    // Set up a click event listener on the map to get latitude and longitude
    map.addListener("click", (event) => {
        placeMarker(event.latLng);
    });
}

// Function to place a marker and update input fields with latitude and longitude
function placeMarker(location) {
    if (marker) {
        marker.setPosition(location);
    } else {
        marker = new google.maps.Marker({
            position: location,
            map: map,
        });
    }
    document.getElementById("latitude_input").value = location.lat().toFixed(6);
    document.getElementById("longitude_input").value = location.lng().toFixed(6);
}

// Function to detect user location via GPS
function detectLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition((position) => {
            const lat = position.coords.latitude;
            const lon = position.coords.longitude;
            const userLocation = { lat, lng: lon };

            map.setCenter(userLocation);
            map.setZoom(12);
            placeMarker(userLocation);
        }, () => {
            alert("Unable to retrieve your location.");
        });
    } else {
        alert("Geolocation is not supported by this browser.");
    }
}

// Function to update map when latitude and longitude are input manually
function updateMap() {
    const lat = parseFloat(document.getElementById("latitude_input").value);
    const lon = parseFloat(document.getElementById("longitude_input").value);

    if (!isNaN(lat) && !isNaN(lon)) {
        const manualLocation = { lat, lng: lon };
        map.setCenter(manualLocation);
        map.setZoom(12);
        placeMarker(manualLocation);
    }
}