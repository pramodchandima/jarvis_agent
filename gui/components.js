class TerminalHeader extends HTMLElement {
    connectedCallback() {
        // If already rendered, do nothing
        if (this.querySelector('.terminal-header')) return;

        const title = this.getAttribute('title') || 'J.A.R.V.I.S. // TERMINAL';
        
        // Save the children nodes to inject into the right side
        const childNodes = Array.from(this.childNodes);

        const headerDiv = document.createElement('div');
        headerDiv.className = 'terminal-header';

        const statusIndicator = document.createElement('div');
        statusIndicator.className = 'status-indicator';
        statusIndicator.innerHTML = `
            <span class="pulse-ring"></span>
            <span class="hud-title">${title}</span>
        `;

        const headerRight = document.createElement('div');
        headerRight.className = 'header-right';
        
        // If there were no children provided, just add the timezone lbl
        const hasElements = childNodes.some(node => node.nodeType === 1 || (node.nodeType === 3 && node.textContent.trim() !== ''));
        if (!hasElements) {
            headerRight.innerHTML = `<div class="timezone-hud" id="timezone-lbl">UTC</div>`;
        } else {
            childNodes.forEach(child => headerRight.appendChild(child));
        }

        headerDiv.appendChild(statusIndicator);
        headerDiv.appendChild(headerRight);

        this.appendChild(headerDiv);
    }
}
customElements.define('terminal-header', TerminalHeader);

class TechCard extends HTMLElement {
    connectedCallback() {
        if (this.querySelector('.card')) return;

        const num = this.getAttribute('num');
        const label = this.getAttribute('label');
        const cornersAttr = this.getAttribute('corners') || ''; // e.g. "tl,tr,bl,br"
        const extClass = this.getAttribute('ext-class') || '';

        // Save existing children to preserve original DOM node references
        const childNodes = Array.from(this.childNodes);

        const cardDiv = document.createElement('div');
        cardDiv.className = `card tech-card ${extClass}`;

        // Add corners
        const corners = cornersAttr.split(',').filter(c => c.trim() !== '');
        corners.forEach(corner => {
            const cornerDiv = document.createElement('div');
            cornerDiv.className = `tech-corner ${corner.trim()}`;
            cardDiv.appendChild(cornerDiv);
        });

        // Add Number
        if (num) {
            const numDiv = document.createElement('div');
            numDiv.className = 'hud-num';
            numDiv.innerText = num;
            cardDiv.appendChild(numDiv);
        }

        // Add Label
        if (label) {
            const lblDiv = document.createElement('div');
            lblDiv.className = 'hud-lbl';
            lblDiv.innerText = label;
            cardDiv.appendChild(lblDiv);
        }

        // Append children to cardDiv directly to preserve original DOM nodes
        childNodes.forEach(child => cardDiv.appendChild(child));

        this.appendChild(cardDiv);
    }
}
customElements.define('tech-card', TechCard);
