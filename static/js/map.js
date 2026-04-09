// Global variables to store the map instance and markers
var map;
var savedCenter = localStorage.getItem('mapCenter');
var savedZoom = localStorage.getItem('mapZoom');

var IRELAND_BOUNDS = L.latLngBounds([51.22, -10.86], [55.73, -5.25]);
var MAP_BOUNDS = IRELAND_BOUNDS.pad(0.35);
var center = savedCenter ? JSON.parse(savedCenter) : [53.35, -8.2];
var zoom = savedZoom ? parseInt(savedZoom, 10) : 7;

function applyIrelandConstraints() {
    map.setMaxBounds(MAP_BOUNDS);
    map.setMinZoom(5);
    map.setMaxZoom(19);
}

function enforceCenterInIreland() {
    if (!MAP_BOUNDS.contains(map.getCenter())) {
        map.panInsideBounds(MAP_BOUNDS, { animate: false });
    }
}

function persistMapState() {
    var currentCenter = map.getCenter();
    var currentZoom = map.getZoom();

    localStorage.setItem('mapCenter', JSON.stringify([currentCenter.lat, currentCenter.lng]));
    localStorage.setItem('mapZoom', currentZoom);
}

function initMap() {
    map = L.map('map', {
        maxBoundsViscosity: 1.0
    }).setView(center, zoom);

    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        minZoom: 5,
        attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    }).addTo(map);

    applyIrelandConstraints();
    enforceCenterInIreland();
    persistMapState();

    map.on('moveend', function() {
        enforceCenterInIreland();
        persistMapState();
    });

    map.on('zoomend', function() {
        enforceCenterInIreland();
        persistMapState();
    });

    map.on('resize', function() {
        applyIrelandConstraints();
        enforceCenterInIreland();
    });

    window.addEventListener('resize', function() {
        map.invalidateSize();
        applyIrelandConstraints();
        enforceCenterInIreland();
    });
}

if (typeof L !== 'undefined') {
    initMap();
} else {
    window.addEventListener('load', function() {
        initMap();
    });
}
