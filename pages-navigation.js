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
}
