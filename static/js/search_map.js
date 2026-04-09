var centerMarker = L.marker([map.getCenter().lat, map.getCenter().lng]).addTo(map)

function setLocation(){
    document.getElementById("latitude").value = map.getCenter().lat;
    document.getElementById("longitude").value = map.getCenter().lng;
}

document.getElementById("latitude").value = map.getCenter().lat;
document.getElementById("longitude").value = map.getCenter().lng;

const radiusSlider = document.getElementById("search-radius");

var tempRad = (parseFloat(radiusSlider.value) || 1) * 1000;

var circle = L.circle(map.getCenter(), {radius: tempRad}).addTo(map);
var bounds = circle.getBounds();
map.removeLayer(circle); 

var square = L.rectangle(bounds, {
    color: "blue",
    weight: 1
}).addTo(map);
square.setBounds(bounds);

radiusSlider.addEventListener('input', function() {
    var radius = this.value;
    radius = radius * 1000;

    var tempCircle = L.circle(map.getCenter(), {radius: (radius)}).addTo(map);
    var newBounds = tempCircle.getBounds();
    
    square.setBounds(newBounds);
    map.removeLayer(tempCircle); 
});

function onDrag(e){
    var center = map.getCenter();
    centerMarker.setLatLng(center);

    var radius = (parseFloat(radiusSlider.value) || 1) * 1000;

    var tempCircle = L.circle(centerMarker.getLatLng(), {radius: radius}).addTo(map);
    square.setBounds(tempCircle.getBounds());
    map.removeLayer(tempCircle);

    document.getElementById("latitude").value = map.getCenter().lat;
    document.getElementById("longitude").value = map.getCenter().lng;
}

map.on("move", onDrag);

const searchForm = document.querySelector(".search-form");
const categoryInput = document.getElementById("search-category");
const typeInput = document.getElementById("search-type");
const filterChips = Array.from(document.querySelectorAll(".filter-chip[data-filter-group][data-filter-value]"));
const searchScrollKey = "trackrebel.search.scrollRatio";
const searchScrollRestoreKey = "trackrebel.search.restoreScroll";

function saveSearchScrollPosition() {
    const maxScroll = Math.max(document.documentElement.scrollHeight - window.innerHeight, 0);
    const scrollRatio = maxScroll > 0 ? window.scrollY / maxScroll : 0;

    sessionStorage.setItem(searchScrollKey, String(scrollRatio));
    sessionStorage.setItem(searchScrollRestoreKey, "true");
}

function restoreSearchScrollPosition() {
    if (sessionStorage.getItem(searchScrollRestoreKey) !== "true") {
        return;
    }

    sessionStorage.removeItem(searchScrollRestoreKey);

    const savedRatio = parseFloat(sessionStorage.getItem(searchScrollKey) || "0");

    if (!Number.isFinite(savedRatio)) {
        return;
    }

    window.requestAnimationFrame(function() {
        const maxScroll = Math.max(document.documentElement.scrollHeight - window.innerHeight, 0);
        window.scrollTo(0, maxScroll * savedRatio);
    });
}

function normalizeFilterValue(input) {
    if (!input) {
        return "all";
    }

    if (!input.value) {
        input.value = "all";
    }

    return input.value;
}

function updateChipState(group, selectedValue) {
    filterChips
        .filter(function(chip) {
            return chip.dataset.filterGroup === group;
        })
        .forEach(function(chip) {
            const isSelected = chip.dataset.filterValue === selectedValue;
            chip.classList.toggle("is-active", isSelected);
            chip.setAttribute("aria-pressed", isSelected ? "true" : "false");
        });
}

if (categoryInput) {
    updateChipState("category", normalizeFilterValue(categoryInput));
}

if (typeInput) {
    updateChipState("type", normalizeFilterValue(typeInput));
}

filterChips.forEach(function(chip) {
    chip.addEventListener("click", function() {
        const group = chip.dataset.filterGroup;
        const selectedValue = chip.dataset.filterValue;

        if (group === "category" && categoryInput) {
            categoryInput.value = selectedValue;
            updateChipState("category", selectedValue);
        }

        if (group === "type" && typeInput) {
            typeInput.value = selectedValue;
            updateChipState("type", selectedValue);
        }
    });
});

if (searchForm) {
    searchForm.addEventListener("submit", function() {
        saveSearchScrollPosition();
    });

    searchForm.addEventListener("reset", function() {
        sessionStorage.removeItem(searchScrollRestoreKey);

        window.setTimeout(function() {
            if (categoryInput) {
                categoryInput.value = "all";
                updateChipState("category", categoryInput.value);
            }

            if (typeInput) {
                typeInput.value = "all";
                updateChipState("type", typeInput.value);
            }
        }, 0);
    });
}

restoreSearchScrollPosition();

