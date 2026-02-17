// static/js/pdv.js

// Usar uma IIFE (Immediately Invoked Function Expression) para isolar o escopo
// e garantir que o script seja executado apenas uma vez, mesmo se carregado múltiplas vezes.
(function() {
    // Verifica se o script já foi inicializado para evitar duplicação de listeners
    if (window.pdvInitialized) {
        console.warn("PDV script já inicializado. Ignorando nova execução.");
        return;
    }
    window.pdvInitialized = true; // Marca como inicializado

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
        const printReceiptModalElement = document.getElementById('printReceiptModal');
        const printReceiptModal = new bootstrap.Modal(printReceiptModalElement);
        const receiptContent = document.getElementById('receipt-content');
        const printBtn = document.getElementById('print-btn');
        const printAllBtn = document.getElementById('print-all-btn'); // Novo botão

        let cart = [];
        let currentReceiptsToPrint = []; // Armazena a lista de HTMLs de cupons

        // Função debounce para limitar a frequência de chamadas de função
        function debounce(func, delay) {
            let timeout;
            return function(...args) {
                const context = this;
                clearTimeout(timeout);
                timeout = setTimeout(() => func.apply(context, args), delay);
            };
        }

        // Função para buscar produtos
        searchInput.addEventListener('input', debounce(function() {
            const query = searchInput.value.trim();
            if (query.length > 1) {
                fetch(`/pdv/search_product?query=${query}`)
                    .then(response => {
                        if (!response.ok) {
                            throw new Error(`HTTP error! status: ${response.status}`);
                        }
                        return response.json();
                    })
                    .then(products => {
                        searchResults.innerHTML = '';
                        if (products.length > 0) {
                            products.forEach(product => {
                                const li = document.createElement('li');
                                li.classList.add('list-group-item', 'list-group-item-action');
                                li.textContent = `${product.name} (R$ ${product.price.toFixed(2)}) - Estoque: ${product.stock}`;
                                li.dataset.productId = product.id;
                                li.dataset.productName = product.name;
                                li.dataset.productPrice = product.price;
                                li.dataset.productStock = product.stock;
                                li.addEventListener('click', addProductToCart);
                                searchResults.appendChild(li);
                            });
                            searchResults.style.display = 'block';
                        } else {
                            searchResults.style.display = 'none';
                        }
                    })
                    .catch(error => {
                        console.error('Erro ao buscar produtos:', error);
                        searchResults.innerHTML = '<li class="list-group-item text-danger">Erro ao buscar produtos.</li>';
                        searchResults.style.display = 'block';
                    });
            } else {
                searchResults.style.display = 'none';
            }
        }, 300)); // Debounce para evitar muitas requisições

        // Função para adicionar produto ao carrinho
        function addProductToCart(event) {
            const productId = parseInt(event.target.dataset.productId);
            const productName = event.target.dataset.productName;
            const productPrice = parseFloat(event.target.dataset.productPrice);
            const productStock = parseInt(event.target.dataset.productStock);

            const existingItem = cart.find(item => item.id === productId);

            if (existingItem) {
                if (existingItem.quantity < productStock) {
                    existingItem.quantity++;
                } else {
                    alert(`Estoque máximo (${productStock}) atingido para ${productName}.`);
                }
            } else {
                if (productStock > 0) {
                    cart.push({
                        id: productId,
                        name: productName,
                        price: productPrice,
                        quantity: 1,
                        stock: productStock // Mantém o estoque original para referência
                    });
                } else {
                    alert(`Produto ${productName} está fora de estoque.`);
                }
            }
            updateCartDisplay();
            searchResults.style.display = 'none'; // Esconde os resultados após adicionar
            searchInput.value = ''; // Limpa o campo de busca
        }

        // Função para atualizar a exibição do carrinho
        function updateCartDisplay() {
            cartItemsContainer.innerHTML = '';
            let total = 0;

            if (cart.length === 0) {
                cartItemsContainer.innerHTML = '<li class="list-group-item text-center text-muted">Carrinho vazio</li>';
                checkoutBtn.disabled = true;
                clearCartBtn.disabled = true;
            } else {
                cart.forEach(item => {
                    const li = document.createElement('li');
                    li.classList.add('list-group-item', 'd-flex', 'justify-content-between', 'align-items-center');
                    li.innerHTML = `
                        <div>
                            ${item.name} <br>
                            <small>R$ ${item.price.toFixed(2)} x ${item.quantity}</small>
                        </div>
                        <div>
                            R$ ${(item.price * item.quantity).toFixed(2)}
                            <button class="btn btn-sm btn-outline-secondary ms-2 decrease-quantity" data-id="${item.id}">-</button>
                            <button class="btn btn-sm btn-outline-secondary increase-quantity" data-id="${item.id}">+</button>
                            <button class="btn btn-sm btn-outline-danger ms-2 remove-item" data-id="${item.id}">x</button>
                        </div>
                    `;
                    cartItemsContainer.appendChild(li);
                    total += item.price * item.quantity;
                });
                checkoutBtn.disabled = false;
                clearCartBtn.disabled = false;
            }
            cartTotalElement.textContent = total.toFixed(2);
            calculateChange();
        }

        // Event listeners para botões de quantidade e remoção no carrinho
        cartItemsContainer.addEventListener('click', function(event) {
            const target = event.target;
            const productId = parseInt(target.dataset.id);
            const item = cart.find(i => i.id === productId);

            if (!item) return;

            if (target.classList.contains('increase-quantity')) {
                if (item.quantity < item.stock) {
                    item.quantity++;
                } else {
                    alert(`Estoque máximo (${item.stock}) atingido para ${item.name}.`);
                }
            } else if (target.classList.contains('decrease-quantity')) {
                if (item.quantity > 1) {
                    item.quantity--;
                } else {
                    // Se a quantidade for 1 e o usuário tentar diminuir, remove o item
                    cart = cart.filter(i => i.id !== productId);
                }
            } else if (target.classList.contains('remove-item')) {
                cart = cart.filter(i => i.id !== productId);
            }
            updateCartDisplay();
        });

        // Limpar carrinho
        clearCartBtn.addEventListener('click', function() {
            if (confirm('Tem certeza que deseja limpar o carrinho?')) {
                cart = [];
                updateCartDisplay();
                paidAmountInput.value = '0.00';
                calculateChange();
            }
        });

        // Calcular troco
        paidAmountInput.addEventListener('input', calculateChange);
        paymentMethodSelect.addEventListener('change', calculateChange);

        function calculateChange() {
            const total = parseFloat(cartTotalElement.textContent);
            const paid = parseFloat(paidAmountInput.value) || 0;
            const paymentMethod = paymentMethodSelect.value;
            let change = paid - total;

            if (paymentMethod !== 'Dinheiro') {
                paidAmountInput.value = total.toFixed(2); // Em cartão/pix, o valor pago é o total
                change = 0;
                paidAmountInput.disabled = true;
            } else {
                paidAmountInput.disabled = false;
            }

            changeAmountElement.textContent = `R$ ${change.toFixed(2)}`;
            if (change < 0) {
                changeAmountElement.classList.remove('text-success');
                changeAmountElement.classList.add('text-danger');
            } else {
                changeAmountElement.classList.remove('text-danger');
                changeAmountElement.classList.add('text-success');
            }
        }

        // Finalizar Venda
        checkoutBtn.addEventListener('click', function() {
            if (cart.length === 0) {
                alert('O carrinho está vazio. Adicione produtos para finalizar a venda.');
                return;
            }

            const total = parseFloat(cartTotalElement.textContent);
            const paid = parseFloat(paidAmountInput.value) || 0;
            const paymentMethod = paymentMethodSelect.value;

            if (paid < total && paymentMethod === 'Dinheiro') {
                alert('O valor pago é insuficiente para finalizar a venda em dinheiro.');
                return;
            }

            const saleData = {
                cart: cart.map(item => ({
                    id: item.id,
                    name: item.name,
                    price: item.price,
                    quantity: item.quantity
                })),
                total_amount: total,
                payment_method: paymentMethod,
                paid_amount: paid,
                change_amount: paid - total
            };

            fetch('/pdv/checkout', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(saleData)
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => { throw new Error(err.message || 'Erro desconhecido no checkout'); });
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    currentReceiptsToPrint = data.receipt_htmls; // Armazena a lista de HTMLs
                    if (currentReceiptsToPrint && currentReceiptsToPrint.length > 0) {
                        // Exibe o primeiro cupom no modal para pré-visualização
                        receiptContent.innerHTML = currentReceiptsToPrint[0];
                        printReceiptModal.show();
                        // Habilita/desabilita o botão "Imprimir Todos"
                        printAllBtn.style.display = currentReceiptsToPrint.length > 1 ? 'block' : 'none';
                    } else {
                        alert('Venda finalizada com sucesso, mas nenhum cupom foi gerado.');
                    }

                    // Limpa o carrinho após a venda bem-sucedida
                    cart = [];
                    updateCartDisplay();
                    paidAmountInput.value = '0.00';
                    calculateChange();
                } else {
                    alert(`Erro ao finalizar venda: ${data.message}`);
                }
            })
            .catch(error => {
                console.error('Erro no checkout:', error);
                alert(`Ocorreu um erro ao finalizar a venda: ${error.message}`);
            });
        });

        // Função para imprimir um único cupom
        function printSingleReceipt(receiptHtml) {
            const printWindow = window.open('', '_blank');
            printWindow.document.write('<html><head><title>Cupom Fiscal</title>');
            printWindow.document.write('<style>');
            printWindow.document.write(`
                body { font-family: 'Consolas', 'Courier New', monospace; font-size: 12px; margin: 0; padding: 10px; }
                .receipt-container { width: 80mm; margin: 0 auto; border: none; padding: 0; }
                .receipt-header, .receipt-body, .receipt-footer { text-align: center; }
                .receipt-body p, .receipt-footer p { margin: 2px 0; }
                .product-name-highlight { font-weight: bold; }
                hr { border-top: 1px dashed #888; margin: 5px 0; }
                /* Estilo para o espaçamento entre cupons */
                .page-break-after {
                    page-break-after: always; /* Força quebra de página na impressão */
                    margin-top: 20mm; /* Espaço físico entre os cupons */
                    border-bottom: 1px dashed #ccc; /* Linha tracejada para corte */
                    padding-bottom: 20mm; /* Espaço abaixo da linha */
                }
                @media print {
                    body { margin: 0; padding: 0; }
                    .receipt-container { border: none; }
                    .page-break-after {
                        page-break-after: always;
                        margin-top: 20mm; /* Garante o espaçamento na impressão */
                        border-bottom: 1px dashed #ccc;
                        padding-bottom: 20mm;
                    }
                }
            `);
            printWindow.document.write('</style></head><body>');
            printWindow.document.write(receiptHtml);
            printWindow.document.write('</body></html>');
            printWindow.document.close();
            printWindow.focus();
            printWindow.print();
            // printWindow.close(); // Comentado para permitir que o usuário feche manualmente se desejar
        }

        // Event listener para o botão "Imprimir Cupom Atual" (no modal, imprime o cupom atualmente exibido)
        printBtn.addEventListener('click', function() {
            if (currentReceiptsToPrint && currentReceiptsToPrint.length > 0) {
                printSingleReceipt(currentReceiptsToPrint[0]); // Imprime apenas o primeiro cupom exibido no modal
                printReceiptModal.hide(); // Esconde o modal após a impressão
            }
        });

        // Event listener para o novo botão "Imprimir Todos os Cupons"
        if (printAllBtn) { // Verifica se o botão existe
            printAllBtn.addEventListener('click', function() {
                if (currentReceiptsToPrint && currentReceiptsToPrint.length > 0) {
                    currentReceiptsToPrint.forEach(receiptHtml => {
                        printSingleReceipt(receiptHtml); // Imprime cada cupom da lista
                    });
                    printReceiptModal.hide(); // Esconde o modal após a impressão de todos
                }
            });
        }

        // Inicializa a exibição do carrinho ao carregar a página
        updateCartDisplay();
        calculateChange();
    });
})(); // Fim da IIFE
