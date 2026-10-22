/**
 * PG Finder Bengaluru - Leaflet OpenStreetMap Integration
 */

function initPGMap(elementId, pins, initialLat = 12.9716, initialLng = 77.5946, zoom = 12) {
  const mapElement = document.getElementById(elementId);
  if (!mapElement || typeof L === 'undefined') return;

  const map = L.map(elementId).setView([initialLat, initialLng], zoom);

  // Free OpenStreetMap Tile Layer
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | PG Finder Bengaluru'
  }).addTo(map);

  if (!pins || pins.length === 0) return map;

  const markers = [];
  const bounds = L.latLngBounds();

  pins.forEach(pin => {
    if (!pin.lat || !pin.lng) return;

    // Custom HTML marker badge with starting rent
    const customIcon = L.divIcon({
      className: 'custom-pg-marker',
      html: `
        <div style="
          background: #0284c7;
          color: white;
          padding: 4px 8px;
          border-radius: 12px;
          font-weight: 700;
          font-size: 11px;
          box-shadow: 0 4px 8px rgba(0,0,0,0.3);
          border: 2px solid white;
          white-space: nowrap;
          display: flex;
          align-items: center;
          gap: 4px;
        ">
          <i class="bi bi-geo-alt-fill"></i> ₹${Number(pin.price).toLocaleString('en-IN')}/m
        </div>
      `,
      iconSize: [80, 28],
      iconAnchor: [40, 14]
    });

    const marker = L.marker([pin.lat, pin.lng], { icon: customIcon }).addTo(map);

    // Popup card preview
    const popupContent = `
      <div style="width: 220px; font-family: 'Plus Jakarta Sans', sans-serif;">
        <img src="${pin.cover_image}" alt="${pin.name}" style="width: 100%; height: 110px; object-fit: cover; border-radius: 6px; margin-bottom: 6px;">
        <div style="font-size: 10px; font-weight: 700; color: #0284c7; text-transform: uppercase;">${pin.locality} • ${pin.gender}</div>
        <div style="font-weight: 700; font-size: 13px; color: #0f172a; margin-bottom: 4px; line-height: 1.2;">${pin.name}</div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 6px;">
          <span style="font-weight: 800; font-size: 14px; color: #0f172a;">₹${Number(pin.price).toLocaleString('en-IN')}<small style="font-size: 10px; color: #64748b;">/mo</small></span>
          <span style="background: #d1fae5; color: #065f46; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px;">${pin.vacant_beds} beds</span>
        </div>
        <a href="${pin.url}" class="btn btn-sm btn-primary w-100 mt-2" style="font-size: 11px; font-weight: 700; padding: 4px 8px; border-radius: 4px;">View Details</a>
      </div>
    `;

    marker.bindPopup(popupContent);
    markers.push(marker);
    bounds.extend([pin.lat, pin.lng]);
  });

  if (markers.length > 1) {
    map.fitBounds(bounds, { padding: [40, 40] });
  } else if (markers.length === 1) {
    map.setView([pins[0].lat, pins[0].lng], 14);
  }

  return map;
}
