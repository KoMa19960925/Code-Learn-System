// Function to show the selected page and hide others
function showPage(pageId, sectionId) {
    // Hide all pages
    const pages = document.querySelectorAll('.page');
    pages.forEach(page => {
        page.classList.remove('active');
    });
    
    // Show the selected page
    document.getElementById(pageId).classList.add('active');
    
    // Scroll to top when changing pages
    if (sectionId) {
        const heading = document.querySelector(`#${sectionId} h2`);
        heading.tabIndex = -1;
        heading.focus();
        heading.scrollIntoView();
    } else {
        window.scrollTo(0, 0);
    }
}
// Form submission handlers
document.addEventListener('DOMContentLoaded', function() {
    // Login form handler
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const email = document.getElementById('loginEmail').value;
            const password = document.getElementById('loginPassword').value;
            
            // Basic validation
            if (!email || !password) {
                alert('Please fill in all fields');
                return;
            }
            
            // Simulate login process
            simulateLogin(email, password);
        });
    }

    // Register form handler
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const name = document.getElementById('registerName').value;
            const email = document.getElementById('registerEmail').value;
            const password = document.getElementById('registerPassword').value;
            const confirmPassword = document.getElementById('registerConfirmPassword').value;
            
            // Validation
            if (!name || !email || !password || !confirmPassword) {
                alert('Please fill in all fields');
                return;
            }
            
            if (password !== confirmPassword) {
                alert('Passwords do not match!');
                return;
            }
            
            if (password.length < 6) {
                alert('Password must be at least 6 characters long');
                return;
            }
            
            // Simulate registration process
            simulateRegistration(name, email, password);
        });
    }
    
    // Initialize the page
    showPage('home');
});

// Simulate login process
function simulateLogin(email, password) {
    // Show loading state
    const loginBtn = document.querySelector('#loginForm .btn-primary');
    const originalText = loginBtn.textContent;
    loginBtn.textContent = 'Logging in...';
    loginBtn.disabled = true;
    
    // Simulate API call
    setTimeout(() => {
        // Reset button
        loginBtn.textContent = originalText;
        loginBtn.disabled = false;
        
        // In a real application, you would handle the server response here
        alert(`Login successful! Welcome back!`);
        
        // Clear form
        document.getElementById('loginForm').reset();
        
        // Redirect to home page or dashboard
        showPage('home');
    }, 1500);
}
// Simulate registration process
function simulateRegistration(name, email, password) {
    // Show loading state
    const registerBtn = document.querySelector('#registerForm .btn-primary');
    const originalText = registerBtn.textContent;
    registerBtn.textContent = 'Creating Account...';
    registerBtn.disabled = true;
    
    // Simulate API call
    setTimeout(() => {
        // Reset button
        registerBtn.textContent = originalText;
        registerBtn.disabled = false;
        
        // In a real application, you would handle the server response here
        alert(`Registration successful! Welcome to Coding Study Hub, ${name}!`);
        
        // Clear form
        document.getElementById('registerForm').reset();
        
        // Redirect to home page
        showPage('home');
    }, 1500);
}
// Add form input enhancements
document.addEventListener('DOMContentLoaded', function() {
    const formInputs = document.querySelectorAll('input, textarea');
    
    formInputs.forEach(input => {
        // Add real-time validation for email fields
        if (input.type === 'email') {
            input.addEventListener('input', function() {
                if (this.value && !isValidEmail(this.value)) {
                    this.style.borderColor = '#e74c3c';
                } else if (this.value) {
                    this.style.borderColor = '#2ecc71';
                }
            });
        }
        
        // Add real-time validation for password fields
        if (input.type === 'password' && input.id.includes('Password')) {
            input.addEventListener('input', function() {
                if (this.value.length > 0 && this.value.length < 6) {
                    this.style.borderColor = '#e74c3c';
                } else if (this.value.length >= 6) {
                    this.style.borderColor = '#2ecc71';
                }
            });
        }
    });
});

// Email validation function
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}
// Password strength indicator (optional enhancement)
function checkPasswordStrength(password) {
    let strength = 0;
    
    if (password.length >= 8) strength++;
    if (/[a-z]/.test(password)) strength++;
    if (/[A-Z]/.test(password)) strength++;
    if (/[0-9]/.test(password)) strength++;
    if (/[^A-Za-z0-9]/.test(password)) strength++;
    
    return strength;
}