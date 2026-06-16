(function (global) {
    function Popup(content, options = {}) {
        this.content = content;
        this.options = Object.assign({
            width: '400px',
            height: '200px',
            backgroundColor: '#fff',
            closeButton: true,
            overlay: true,
            fixed: true,
            top: '50%',
            left: '50%',
            classes: [],
            element: document.body
        }, options);

        this.init();
    }

    Popup.prototype.init = function () {
        this.overlay = null;
        this.oldOverflow = this.options.element.style.overflow;
        this.popupContainer = document.createElement('div');
        this.popupContainer.classList.add('popup-container');
        this.popupContainer.style.position = this.options.fixed ? 'fixed' : 'absolute';
        this.popupContainer.style.top = this.options.top;
        this.popupContainer.style.left = this.options.left;
        this.popupContainer.style.transform = 'translate(-50%, -50%)';
        this.popupContainer.style.width = this.options.width;
        this.popupContainer.style.height = this.options.height;
        this.popupContainer.style.backgroundColor = this.options.backgroundColor;
        this.popupContainer.style.boxShadow = '0px 0px 15px rgba(0, 0, 0, 0.3)';
        this.popupContainer.style.zIndex = '10000';
        this.popupContainer.style.padding = '20px';
        this.popupContainer.style.borderRadius = '8px';
        this.popupContainer.style.display = 'flex';
        this.popupContainer.style.flexDirection = 'column';
        this.popupContainer.style.justifyContent = 'start';
        this.popupContainer.style.alignItems = 'start';
        for (let i = 0; i < this.options.classes.length; i++) {
            this.popupContainer.classList.add(this.options.classes[i]);
        }

        this.popupContainer.innerHTML = this.content;

        if (this.options.closeButton) {
            this.closeButton = document.createElement('button');

            this.closeButton.style.color = '#fff';
            this.closeButton.style.border = 'none';
            this.closeButton.style.cursor = 'pointer';
            this.closeButton.style.borderRadius = '4px';
            this.closeButton.style.position = this.options.fixed ? 'fixed' : 'absolute';
            this.closeButton.style.top = '2px';
            this.closeButton.style.right = '2px';
            this.closeButton.style.backgroundColor = 'transparent';
            this.closeButton.style.color = '#000';

            this.closeButton.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="black" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>';
            this.closeButton.addEventListener('click', () => {
                this.closePopup();
            });

            this.popupContainer.appendChild(this.closeButton);
        }


        if (this.options.overlay) {
            this.overlay = document.createElement('div');
            this.overlay.classList.add('popup-overlay');
            this.overlay.style.position = this.options.fixed ? 'fixed' : 'absolute';
            this.overlay.style.top = '0';
            this.overlay.style.left = '0';
            this.overlay.style.width = '100vw';
            this.overlay.style.height = '100vh';
            this.overlay.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
            this.overlay.style.zIndex = '9999';
            if (this.options.closeButton) {
                this.overlay.addEventListener('click', () => {
                    this.closePopup();
                });
            }
            this.options.element.appendChild(this.overlay);
        }

        this.options.element.appendChild(this.popupContainer);
        this.options.element.style.overflow = 'hidden';
    };

    Popup.prototype.closePopup = function() {
        if (this.popupContainer && this.popupContainer.parentNode) {
            this.popupContainer.parentNode.removeChild(this.popupContainer);
        }

        if (this.overlay && this.overlay.parentNode) {
            this.overlay.parentNode.removeChild(this.overlay);
        }
        this.options.element.style.overflow = this.oldOverflow;

    };


    global.Popup = Popup;

})(window);

