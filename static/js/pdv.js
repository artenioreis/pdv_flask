// static/js/pdv.js
document.addEventListener('DOMContentLoaded', function() {
    const productSearchInput = document.getElementById('productSearch');
    const searchResultsDiv = document.getElementById('searchResults');
    const cartItemsBody = document.getElementById('cartItems');
    const cartTotalSpan = document.getElementById('cartTotal');
    const paymentMethodSelect = document.getElementById('paymentMethod');
    const checkoutBtn = document = document.getElementById('checkoutBtn');
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
            cart[existingItemIndex].quantity++;
        } else {
            cart.push({
                id: product.id,
                name: product.name,
                price: product.price,
                stock: product.stock,
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

        if (query.length < 2) {
            searchResultsDiv.innerHTML = '';
            return;
        }

        searchTimeout = setTimeout(() => {
            fetch(`/pdv/search_product?query=${query}`)
                .then(response => response.json())
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
                .catch(error => console.error('Erro na busca de produtos:', error));
        }, 300);
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

            if (isNaN(newQuantity) || newQuantity < 1) {
                newQuantity = 1;
                event.target.value = 1;
            }

            cart[index].quantity = newQuantity;
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
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(data.message);
                cart = [];
                updateCartDisplay();
                currentReceipts = data.receipt_htmls;

                if (currentReceipts.length > 0) {
                    receiptModalLabel.textContent = `Cupons Gerados (${currentReceipts.length} itens)`;
                    receiptContentDiv.innerHTML = `
                        <p>Foram gerados <strong>${currentReceipts.length}</strong> cupons não fiscais para esta venda.</p>
                        <p>Clique em "Imprimir" para enviar todos os cupons para a impressora.</p>
                        <hr>
                        <h6>Pré-visualização do primeiro cupom:</h6>
                        <div style="border: 1px solid #eee; padding: 10px; max-height: 300px; overflow-y: auto;">
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
            alert('Ocorreu um erro ao processar a venda.');
        });
    });

    clearCartBtn.addEventListener('click', function() {
        if (confirm('Tem certeza que deseja limpar o carrinho?')) {
            cart = [];
            updateCartDisplay();
        }
    });

    // --- Lógica de impressão ajustada para usar iframes temporários ---
    printReceiptBtn.addEventListener('click', function() {
        if (currentReceipts.length === 0) {
            alert('Nenhum cupom para imprimir.');
            return;
        }

        // Função para imprimir um único cupom usando um iframe
        function printSingleReceipt(receiptHtml) {
            const iframe = document.createElement('iframe');
            iframe.style.display = 'none'; // Oculta o iframe
            document.body.appendChild(iframe); // Adiciona ao corpo do documento

            const iframeDoc = iframe.contentWindow.document;
            iframeDoc.open();
            iframeDoc.write(receiptHtml); // Escreve o HTML do cupom no iframe
            iframeDoc.close();

            iframe.contentWindow.focus();
            iframe.contentWindow.print(); // Imprime o conteúdo do iframe

            // Remove o iframe após um pequeno atraso para garantir que a impressão foi iniciada
            setTimeout(() => {
                document.body.removeChild(iframe);
            }, 1000); // 1 segundo de atraso
        }

        // Itera sobre cada cupom e o imprime com um pequeno atraso entre eles
        // para evitar sobrecarregar a fila de impressão e o navegador
        let delay = 0;
        currentReceipts.forEach((receiptHtml, index) => {
            setTimeout(() => {
                printSingleReceipt(receiptHtml);
            }, delay);
            delay += 1500; // Atraso de 1.5 segundos entre cada impressão
        });

        receiptModal.hide(); // Fecha o modal após iniciar a impressão
    });

    updateCartDisplay();
});
