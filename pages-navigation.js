const learningServer = document.querySelector('meta[name="learning-server"]').content.trim();

if (learningServer) {
    const backend = new URL(learningServer, document.baseURI);
    if (backend.protocol === 'https:') {
        for (const link of document.querySelectorAll('a[data-route]')) {
            const destination = new URL(link.dataset.route, backend.origin + '/');
            if (link.dataset.section) {
                destination.searchParams.set('section', link.dataset.section);
                destination.hash = link.dataset.section;
            }
            link.href = destination.href;
        }
        if (location.hash === '#learning-access') {
            location.replace(new URL('/coding', backend));
        }
    }
} else {
    startPortfolioDemo();
}

function startPortfolioDemo() {
    const accountKey = 'code-learn-demo-accounts';
    const sessionKey = 'code-learn-demo-session';
    const main = document.querySelector('main');
    const auth = document.querySelector('.auth-buttons');
    const forms = [...main.querySelectorAll('form')];
    const logout = document.createElement('button');
    logout.type = 'button';
    logout.className = 'btn btn-login';
    logout.textContent = 'Log out';
    auth.append(logout);

    let signedIn = false;
    let nextSection = '';

    function notice(form, message) {
        let status = form.querySelector('.form-notice');
        if (!status) {
            status = document.createElement('p');
            status.className = 'form-notice';
            status.setAttribute('role', 'status');
            form.prepend(status);
        }
        status.textContent = message;
    }

    async function passwordHash(password, salt) {
        const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(password), 'PBKDF2', false, ['deriveBits']);
        const bytes = await crypto.subtle.deriveBits({
            name: 'PBKDF2', salt: Uint8Array.from(salt), iterations: 600000, hash: 'SHA-256'
        }, key, 256);
        return Array.from(new Uint8Array(bytes)).join(',');
    }

    function accounts() {
        return JSON.parse(localStorage.getItem(accountKey) || '{}');
    }

    function show(page) {
        for (const section of main.querySelectorAll('.page')) {
            section.classList.toggle('active', section.id === page);
        }
        window.scrollTo(0, 0);
    }

    async function navigate() {
        const hash = location.hash;
        const [route, section] = hash.slice(1).split('/');
        if (route === 'top') {
            window.scrollTo(0, 0);
            return;
        }

        auth.querySelectorAll('a').forEach(link => { link.hidden = signedIn; });
        logout.hidden = !signedIn;

        if (route === 'learning-access' || (route === 'coding' && !signedIn)) {
            nextSection = section || '';
            notice(forms[0], 'Log in to open Coding Topics. New here? Create an account first.');
            location.replace('#login');
            return;
        }

        if (route !== 'coding') {
            show(['about', 'login', 'register'].includes(route) ? route : 'home');
            return;
        }

        try {
            if (!main.querySelector('#coding')) {
                const response = await fetch('coding-content.html');
                if (!response.ok) throw new Error('Lesson request failed');
                const markup = await response.text();
                if (!signedIn || location.hash !== hash) return;
                if (!main.querySelector('#coding')) main.insertAdjacentHTML('beforeend', markup);
            }
            show('coding');
            document.getElementById(section)?.scrollIntoView();
        } catch {
            if (location.hash === hash) {
                document.querySelector('#learning-access p').textContent = 'Coding Topics could not load. Please refresh and try again.';
                show('learning-access');
            }
        }
    }

    for (const link of main.ownerDocument.querySelectorAll('a[data-route]')) {
        const { route, section } = link.dataset;
        link.href = '#' + route + (section ? '/' + section : '');
    }

    for (const form of forms) {
        const hint = document.createElement('p');
        hint.textContent = 'Portfolio demo. Use a test email and password. Your account stays in this browser.';
        form.before(hint);
        form.addEventListener('submit', async event => {
            event.preventDefault();
            const button = form.querySelector('[type="submit"]');
            const fields = new FormData(form);
            const email = fields.get('email').trim().toLowerCase();
            const password = fields.get('password');
            button.disabled = true;

            try {
                if (form.id === 'registerForm') {
                    if (password !== fields.get('confirmation')) {
                        notice(form, 'Passwords do not match.');
                        return;
                    }
                    const salt = Array.from(crypto.getRandomValues(new Uint8Array(16)));
                    const hash = await passwordHash(password, salt);
                    const saved = accounts();
                    if (Object.hasOwn(saved, email)) {
                        notice(form, 'That email is already registered. Log in to continue.');
                        return;
                    }
                    saved[email] = { salt, hash };
                    localStorage.setItem(accountKey, JSON.stringify(saved));
                    forms[0].elements.email.value = email;
                    notice(forms[0], 'Account created. Log in to start learning.');
                    location.hash = 'login';
                } else {
                    const account = accounts()[email];
                    if (!account || await passwordHash(password, account.salt) !== account.hash) {
                        notice(form, 'Email or password is incorrect.');
                        return;
                    }
                    sessionStorage.setItem(sessionKey, email);
                    signedIn = true;
                    location.hash = nextSection ? 'coding/' + nextSection : 'coding';
                    nextSection = '';
                }
                form.reset();
                form.querySelector('.form-notice')?.remove();
            } catch {
                notice(form, 'Demo login needs browser storage and a secure connection.');
            } finally {
                button.disabled = false;
            }
        });
    }

    logout.addEventListener('click', () => {
        sessionStorage.removeItem(sessionKey);
        signedIn = false;
        main.querySelector('#coding')?.remove();
        location.hash = 'home';
        navigate();
    });

    try {
        const email = sessionStorage.getItem(sessionKey);
        signedIn = Boolean(email && Object.hasOwn(accounts(), email));
    } catch {
        signedIn = false;
    }

    document.querySelector('.back-to-top').addEventListener('click', event => {
        event.preventDefault();
        window.scrollTo(0, 0);
    });

    document.body.classList.add('browser-demo');
    window.addEventListener('hashchange', navigate);
    navigate();
}
