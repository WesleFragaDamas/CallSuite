// static/js/main.js
document.addEventListener('DOMContentLoaded', function() {
    const menuToggleLeft = document.getElementById('menu-toggle-left');
    const sidebarWrapperLeft = document.getElementById('sidebar-wrapper-left');

    if (menuToggleLeft && sidebarWrapperLeft) {
        menuToggleLeft.addEventListener('click', function() {
            sidebarWrapperLeft.classList.toggle('d-none'); // Simples toggle com display none
        });
    }

    const menuToggleRight = document.getElementById('menu-toggle-right');
    const sidebarWrapperRight = document.getElementById('sidebar-wrapper-right');

    if (menuToggleRight && sidebarWrapperRight) {
        menuToggleRight.addEventListener('click', function() {
            sidebarWrapperRight.classList.toggle('d-none');
        });
    }
//--------------------------------------------------------------------------------//

    const statusBadge = computadorCard.querySelector('.status-reportado-badge');
if (statusBadge) {
    statusBadge.textContent = data.novo_status_computador;
    statusBadge.className = 'status-reportado-badge badge bg-danger'; // Ajuste conforme necessário
}
});