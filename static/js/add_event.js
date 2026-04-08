const latInput = document.getElementById('latitude');
const lngInput = document.getElementById('longitude');
const coordDisplay = document.getElementById('coord-display');

let marker = null;

const updateCoordinates = (lat, lng) => {
latInput.value = lat.toFixed(6);
lngInput.value = lng.toFixed(6);
coordDisplay.textContent = `Selected: ${latInput.value}, ${lngInput.value}`;
};

map.on('click', (e) => {
const { lat, lng } = e.latlng;

if (!marker) {
    marker = L.marker([lat, lng]).addTo(map);
} else {
    marker.setLatLng([lat, lng]);
}

updateCoordinates(lat, lng);
});

if (latInput.value && lngInput.value) {
const savedLat = parseFloat(latInput.value);
const savedLng = parseFloat(lngInput.value);
marker = L.marker([savedLat, savedLng]).addTo(map);
map.setView([savedLat, savedLng], 12);
updateCoordinates(savedLat, savedLng);
}