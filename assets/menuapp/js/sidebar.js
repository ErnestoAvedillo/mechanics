document.addEventListener('DOMContentLoaded', function() {
    const menuToggle = document.querySelector('.menu-toggle');
    const sidebar = document.querySelector('.sidebar');
    const sidebarOverlay = document.querySelector('.sidebar-overlay');
    
    // Open/close the menu when clicking the button
    menuToggle.addEventListener('click', function() {
        sidebar.classList.toggle('active');
        menuToggle.classList.toggle('active');
        sidebarOverlay.classList.toggle('active');
    });
    
    // Close the menu when clicking the overlay
    sidebarOverlay.addEventListener('click', function() {
        sidebar.classList.remove('active');
        menuToggle.classList.remove('active');
        sidebarOverlay.classList.remove('active');
    });
    
    // Close the menu when clicking a link
    const sidebarLinks = document.querySelectorAll('.sidebar-menu a');
    sidebarLinks.forEach(link => {
        link.addEventListener('click', function() {
            sidebar.classList.remove('active');
            menuToggle.classList.remove('active');
            sidebarOverlay.classList.remove('active');
        });
    });
    
    // Close the menu with the ESC key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            sidebar.classList.remove('active');
            menuToggle.classList.remove('active');
            sidebarOverlay.classList.remove('active');
        }
    });
});
