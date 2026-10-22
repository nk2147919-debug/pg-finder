/**
 * PG Finder Bengaluru - Main Client JavaScript
 */

document.addEventListener('DOMContentLoaded', function () {
  // Auto-dismiss alerts after 5 seconds
  const alerts = document.querySelectorAll('.alert-dismissible');
  alerts.forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) bsAlert.close();
    }, 5000);
  });

  // Handle AJAX favourite toggling
  const favButtons = document.querySelectorAll('.fav-btn-action');
  favButtons.forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      const propId = btn.getAttribute('data-property-id');
      if (!propId) return;

      const heartIcon = btn.querySelector('i');

      fetch(`/favourite/toggle/${propId}`, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'Content-Type': 'application/json'
        }
      })
      .then(response => {
        if (response.redirected) {
          window.location.href = response.url;
          return null;
        }
        return response.json();
      })
      .then(data => {
        if (!data) return;
        if (data.is_favourite) {
          btn.classList.add('active');
          if (heartIcon) {
            heartIcon.classList.remove('bi-heart');
            heartIcon.classList.add('bi-heart-fill');
            heartIcon.style.color = '#e11d48';
          }
        } else {
          btn.classList.remove('active');
          if (heartIcon) {
            heartIcon.classList.remove('bi-heart-fill');
            heartIcon.classList.add('bi-heart');
            heartIcon.style.color = '';
          }
        }
      })
      .catch(err => {
        console.error('Error toggling favourite:', err);
      });
    });
  });

  // PG Comparison Feature: Local Storage helper
  window.addToCompare = function (propId) {
    let compareList = JSON.parse(localStorage.getItem('pg_compare_ids') || '[]');
    if (!compareList.includes(propId)) {
      if (compareList.length >= 4) {
        alert('You can compare a maximum of 4 properties at once.');
        return;
      }
      compareList.push(propId);
      localStorage.setItem('pg_compare_ids', JSON.stringify(compareList));
      alert('Added to comparison list!');
    } else {
      alert('This property is already in your comparison list.');
    }
    updateCompareBadge();
  };

  window.removeFromCompare = function (propId) {
    let compareList = JSON.parse(localStorage.getItem('pg_compare_ids') || '[]');
    compareList = compareList.filter(id => id !== propId);
    localStorage.setItem('pg_compare_ids', JSON.stringify(compareList));
    updateCompareBadge();
  };

  function updateCompareBadge() {
    const compareList = JSON.parse(localStorage.getItem('pg_compare_ids') || '[]');
    const badge = document.getElementById('compare-count-badge');
    if (badge) {
      badge.textContent = compareList.length;
      badge.style.display = compareList.length > 0 ? 'inline-block' : 'none';
    }
    const compareLink = document.getElementById('nav-compare-link');
    if (compareLink && compareList.length > 0) {
      compareLink.href = `/compare?ids=${compareList.join(',')}`;
    }
  }

  updateCompareBadge();
});
