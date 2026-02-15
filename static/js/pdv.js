// static/js/pdv.js
document.addEventListener('DOMContentLoaded', function() {
    const productSearchInput = document.getElementById('productSearch');
    const searchResultsDiv = document.getElementById('searchResults');
    const cartItemsBody = document.getElementById('cartItems');
    const cartTotalSpan = document.getElementById('cartTotal');
    const paymentMethodSelect = document.getElementById('paymentMethod');
    const checkoutBtn = document.getElementById('checkoutBtn');
    const clearCartBtn = document.getElementById('clearCartBtn');
    const receiptModal = new bootstrap.Modal(document.getElementById('receiptModal'));
    const receiptContentDiv = document.getElementById('receiptContent');
    const printReceiptBtn = document.getElementById('printReceiptBtn');
    const receiptModalLabel = document.getElementById('receiptModalLabel');

    let cart = [];
    let currentReceipts = [];

    function updateCartDisplay() {
        cartItemsBody.innerHTML = '';
        let total = 0;

        if (cart.length === 0) {
            cartItemsBody.innerHTML = '<tr><td colspan="5" class="text-center">Nenhum item no carrinho.</td></tr>';
        } else {
            cart.forEach((item, index) => {
                const subtotal = item.price * item.quantity;
                total += subtotal;
                const row = `
                    <tr>
                        <td>${item.name}</td>
                        <td>
                            <input type="number" class="form-control form-control-sm quantity-input" data-index="${index}" value="${item.quantity}" min="1" style="width: 70px;">
                        </td>
                        <td>R$ ${item.price.toFixed(2)}</td>
                        <td>R$ ${subtotal.toFixed(2)}</td>
                        <td>
                            <button class="btn btn-danger btn-sm remove-item-btn" data-index="${index}">Remover</button>
                        </td>
                    </tr>
                `;
                cartItemsBody.insertAdjacentHTML('beforeend', row);
            });
        }
        cartTotalSpan.textContent = `R$ ${total.toFixed(2)}`;
    }

    function addProductToCart(product) {
        const existingItemIndex = cart.findIndex(item => item.id === product.id);

        if (existingItemIndex > -1) {
            // Verifica se adicionar mais um item excederia o estoque
            if (cart[existingItemIndex].quantity + 1 > product.stock) {
                alert(`Estoque insuficiente para ${product.name}. Disponível: ${product.stock}`);
                return;
            }
            cart[existingItemIndex].quantity++;
        } else {
            // Verifica se o estoque permite adicionar o primeiro item
            if (product.stock < 1) {
                alert(`Estoque insuficiente para ${product.name}. Disponível: ${product.stock}`);
                return;
            }
            cart.push({
                id: product.id,
                name: product.name,
                price: product.price,
                stock: product.stock, // Armazena o estoque atual do produto
                quantity: 1
            });
        }
        updateCartDisplay();
        productSearchInput.value = '';
        searchResultsDiv.innerHTML = '';
    }

    let searchTimeout;
    productSearchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        const query = this.value.trim();

        if (query.length < 2) { // Começa a buscar com pelo menos 2 caracteres
            searchResultsDiv.innerHTML = '';
            return;
        }

        searchTimeout = setTimeout(() => {
            fetch(`/pdv/search_product?query=${encodeURIComponent(query)}`) // encodeURIComponent para caracteres especiais
                .then(response => {
                    if (!response.ok) {
                        // Se a resposta não for OK (ex: 500 Internal Server Error)
                        console.error('Erro na resposta da busca:', response.status, response.statusText);
                        return response.json().then(err => { throw new Error(err.error || 'Erro desconhecido'); });
                    }
                    return response.json();
                })
                .then(products => {
                    searchResultsDiv.innerHTML = '';
                    if (products.length === 0) {
                        searchResultsDiv.innerHTML = '<div class="list-group-item">Nenhum produto encontrado.</div>';
                    } else {
                        products.forEach(product => {
                            const itemDiv = document.createElement('div');
                            itemDiv.classList.add('list-group-item', 'list-group-item-action');
                            itemDiv.textContent = `${product.name} (R$ ${product.price.toFixed(2)}) - Estoque: ${product.stock}`;
                            itemDiv.dataset.product = JSON.stringify(product);
                            itemDiv.addEventListener('click', function() {
                                addProductToCart(JSON.parse(this.dataset.product));
                            });
                            searchResultsDiv.appendChild(itemDiv);
                        });
                    }
                })
                .catch(error => {
                    console.error('Erro na requisição de busca de produtos:', error);
                    searchResultsDiv.innerHTML = `<div class="list-group-item text-danger">Erro ao buscar produtos: ${error.message || error}</div>`;
                });
        }, 300); // Debounce de 300ms
    });

    // Esconde os resultados da busca ao clicar fora
    document.addEventListener('click', function(event) {
        if (!productSearchInput.contains(event.target) && !searchResultsDiv.contains(event.target)) {
            searchResultsDiv.innerHTML = '';
        }
    });

    cartItemsBody.addEventListener('click', function(event) {
        if (event.target.classList.contains('remove-item-btn')) {
            const index = parseInt(event.target.dataset.index);
            cart.splice(index, 1);
            updateCartDisplay();
        }
    });

    cartItemsBody.addEventListener('change', function(event) {
        if (event.target.classList.contains('quantity-input')) {
            const index = parseInt(event.target.dataset.index);
            let newQuantity = parseInt(event.target.value);
            const productInCart = cart[index];

            if (isNaN(newQuantity) || newQuantity < 1) {
                newQuantity = 1; // Garante que a quantidade mínima seja 1
                event.target.value = 1;
            }

            // Verifica o estoque disponível (o estoque original do produto)
            if (newQuantity > productInCart.stock) {
                alert(`Estoque insuficiente para ${productInCart.name}. Disponível: ${productInCart.stock}`);
                newQuantity = productInCart.stock; // Ajusta para o máximo disponível
                event.target.value = productInCart.stock;
            }

            productInCart.quantity = newQuantity;
            updateCartDisplay();
        }
    });

    checkoutBtn.addEventListener('click', function() {
        if (cart.length === 0) {
            alert('O carrinho está vazio. Adicione produtos para finalizar a venda.');
            return;
        }

        const totalAmount = parseFloat(cartTotalSpan.textContent.replace('R$ ', ''));
        const paymentMethod = paymentMethodSelect.value;

        fetch('/pdv/checkout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                cart: cart,
                payment_method: paymentMethod,
                total_amount: totalAmount
            })
        })
        .then(response => {
            if (!response.ok) {
                // Se a resposta não for OK, tenta ler a mensagem de erro do backend
                return response.json().then(err => { throw new Error(err.message || 'Erro desconhecido ao finalizar venda'); });
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                alert(data.message);
                cart = []; // Limpa o carrinho
                updateCartDisplay();
                currentReceipts = data.receipt_htmls; // Armazena a lista de HTMLs

                if (currentReceipts && currentReceipts.length > 0) {
                    // Ajusta o título e o conteúdo do modal para indicar múltiplos cupons
                    receiptModalLabel.textContent = `Cupons Gerados (${currentReceipts.length} itens)`;
                    receiptContentDiv.innerHTML = `
                        <p>Foram gerados <strong>${currentReceipts.length}</strong> cupons não fiscais para esta venda.</p>
                        <p>Clique em "Imprimir" para enviar todos os cupons para a impressora.</p>
                        <hr>
                        <h6>Pré-visualização do primeiro cupom:</h6>
                        <div style="border: 1px solid #eee; padding: 10px; background-color: #f9f9f9; max-height: 250px; overflow-y: auto;">
                            ${currentReceipts[0]}
                        </div>
                    `;
                    receiptModal.show();
                } else {
                    alert('Nenhum cupom gerado.');
                }
            } else {
                alert('Erro ao finalizar venda: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Erro na requisição de checkout:', error);
            alert('Ocorreu um erro ao processar a venda: ' + error.message);
        });
    });

    clearCartBtn.addEventListener('click', function() {
        if (confirm('Tem certeza que deseja limpar o carrinho?')) {
            cart = [];
            updateCartDisplay();
        }
    });

    printReceiptBtn.addEventListener('click', function() {
        if (currentReceipts.length === 0) {
            alert('Nenhum cupom para imprimir.');
            return;
        }

        currentReceipts.forEach((receiptHtml, index) => {
            const printWindow = window.open('', '_blank');
            printWindow.document.write('<html><head><title>Cupom ' + (index + 1) + '</title>');
            const styleMatch = receiptHtml.match(/<style[^>]*>([\s\S]*?)<\/style>/i);
            if (styleMatch && styleMatch[1]) {
                printWindow.document.write('<style>' + styleMatch[1] + '</style>');
            }
            printWindow.document.write('</head><body>');
            const bodyMatch = receiptHtml.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
            if (bodyMatch && bodyMatch[1]) {
                printWindow.document.write(bodyMatch[1]);
            } else {
                printWindow.document.write(receiptHtml);
            }
            printWindow.document.close();
            printWindow.focus();
            printWindow.print();
        });
        receiptModal.hide();
    });

    updateCartDisplay();
});
