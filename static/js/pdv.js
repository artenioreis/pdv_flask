// static/js/pdv.js
(function() {
    if (window.pdvInitialized) return;
    window.pdvInitialized = true;

    document.addEventListener('DOMContentLoaded', function() {
        const searchInput = document.getElementById('product-search');
        const searchResults = document.getElementById('search-results');
        const cartItemsContainer = document.getElementById('cart-items');
        const cartTotalElement = document.getElementById('cart-total');
        const checkoutBtn = document.getElementById('checkout-btn');
        const paymentMethodSelect = document.getElementById('payment-method');
        const paidAmountInput = document.getElementById('paid-amount');
        const changeAmountElement = document.getElementById('change-amount');
        const clearCartBtn = document.getElementById('clear-cart-btn');
        const printReceiptModal = new bootstrap.Modal(document.getElementById('printReceiptModal'));
        const receiptContent = document.getElementById('receipt-content');
        const printBtn = document.getElementById('print-btn');
        const printAllBtn = document.getElementById('print-all-btn');

        let cart = [];
        let receipts = [];

        // Atalhos de Teclado
        document.addEventListener('keydown', e => {
            if (e.key === 'F2') { e.preventDefault(); searchInput.focus(); }
            if (e.key === 'F10' && !checkoutBtn.disabled) { e.preventDefault(); checkoutBtn.click(); }
        });

        // Adicionar com Enter
        searchInput.addEventListener('keydown', e => {
            if (e.key === 'Enter') {
                e.preventDefault();
                const first = searchResults.querySelector('li');
                if (first) first.click();
            }
        });

        // Função Global para Deletar Item
        window.removeItem = function(id) {
            cart = cart.filter(i => i.id !== id);
            updateCart();
        };

        function updateCart() {
            cartItemsContainer.innerHTML = cart.length ? '' : '<li class="list-group-item text-center text-muted">Carrinho vazio</li>';
            let total = 0;
            cart.forEach(item => {
                const li = document.createElement('li');
                li.className = 'list-group-item d-flex justify-content-between align-items-center';
                li.innerHTML = `
                    <div style="font-weight: bold;">${item.name} (${item.quantity}x)</div>
                    <div>
                        <span class="badge bg-dark me-2">R$ ${(item.price * item.quantity).toFixed(2)}</span>
                        <button class="btn btn-sm btn-danger" onclick="removeItem(${item.id})">X</button>
                    </div>`;
                cartItemsContainer.appendChild(li);
                total += item.price * item.quantity;
            });
            
            const totalStr = total.toFixed(2);
            cartTotalElement.textContent = totalStr;
            
            // Ajuste: Preencher valor pago com o total automaticamente
            if (cart.length > 0) {
                paidAmountInput.value = totalStr;
            } else {
                paidAmountInput.value = "0.00";
            }
            
            calculateChange();
        }

        function calculateChange() {
            const total = parseFloat(cartTotalElement.textContent) || 0;
            const paid = parseFloat(paidAmountInput.value) || 0;
            const method = paymentMethodSelect.value;
            const change = paid - total;

            changeAmountElement.textContent = `R$ ${change.toFixed(2)}`;
            
            // Regra de ativação do botão Finalizar
            if (cart.length === 0) {
                checkoutBtn.disabled = true;
                clearCartBtn.disabled = true;
                changeAmountElement.className = 'text-muted';
            } else {
                clearCartBtn.disabled = false;
                if (method === 'Dinheiro') {
                    // Só ativa se o valor pago cobrir o total
                    if (change >= 0) {
                        checkoutBtn.disabled = false;
                        changeAmountElement.className = 'text-success font-weight-bold';
                    } else {
                        checkoutBtn.disabled = true;
                        changeAmountElement.className = 'text-danger';
                    }
                } else {
                    // Outros métodos ativam direto (considera-se pago o valor exato)
                    checkoutBtn.disabled = false;
                    changeAmountElement.className = 'text-success';
                }
            }
        }

        // Listeners para atualizar troco e botão
        paidAmountInput.oninput = calculateChange;
        paymentMethodSelect.onchange = calculateChange;

        // Limpar Carrinho
        clearCartBtn.onclick = () => { cart = []; updateCart(); };

        // Busca de Produtos
        searchInput.oninput = () => {
            const q = searchInput.value.trim();
            if (q.length > 0) {
                fetch(`/pdv/search_product?query=${q}`).then(r => r.json()).then(data => {
                    searchResults.innerHTML = '';
                    if (data.length > 0) {
                        data.forEach(p => {
                            const li = document.createElement('li');
                            li.className = 'list-group-item list-group-item-action';
                            li.textContent = `[${p.id}] ${p.name} - R$ ${p.price.toFixed(2)}`;
                            li.onclick = () => {
                                const ex = cart.find(i => i.id === p.id);
                                if (ex) {
                                    if(ex.quantity < p.stock) ex.quantity++;
                                    else alert('Limite de estoque atingido');
                                } else {
                                    if(p.stock > 0) cart.push({...p, quantity: 1});
                                    else alert('Produto sem estoque');
                                }
                                updateCart(); searchInput.value = ''; searchResults.style.display = 'none'; searchInput.focus();
                            };
                            searchResults.appendChild(li);
                        });
                        searchResults.style.display = 'block';
                    } else {
                        searchResults.style.display = 'none';
                    }
                });
            } else searchResults.style.display = 'none';
        };

        // Finalizar Venda
        checkoutBtn.onclick = () => {
            const total = parseFloat(cartTotalElement.textContent);
            const paid = parseFloat(paidAmountInput.value) || 0;
            const data = { 
                cart, 
                total_amount: total, 
                payment_method: paymentMethodSelect.value, 
                paid_amount: paid, 
                change_amount: paid - total 
            };
            
            fetch('/pdv/checkout', { 
                method: 'POST', 
                headers: {'Content-Type': 'application/json'}, 
                body: JSON.stringify(data) 
            })
            .then(r => r.json()).then(res => {
                if (res.success) {
                    receipts = res.receipt_htmls;
                    receiptContent.innerHTML = receipts[0];
                    printAllBtn.style.display = receipts.length > 1 ? 'block' : 'none';
                    printReceiptModal.show();
                    cart = []; updateCart();
                } else alert('Erro: ' + res.message);
            })
            .catch(() => alert('Erro na comunicação com o servidor'));
        };

        // Impressão
        function printSingle(html) {
            const win = window.open('', '_blank');
            win.document.write(`<html><body onload="window.print();window.close()">${html}</body></html>`);
            win.document.close();
        }

        printBtn.onclick = () => printSingle(receipts[0]);
        printAllBtn.onclick = () => receipts.forEach(printSingle);

        updateCart();
    });
})();