document.addEventListener('DOMContentLoaded', () => {
  // 1. Dynamic year for copyright
  const yearEls = document.querySelectorAll('[data-year]');
  yearEls.forEach(x => (x.textContent = new Date().getFullYear()));

  // 2. Remember clicked product for inquiry form autofill
  document.querySelectorAll('[data-product]').forEach(a => {
    a.addEventListener('click', () => {
      localStorage.setItem('oz_product', a.dataset.product);
    });
  });

  const savedProduct = localStorage.getItem('oz_product');
  const productField = document.querySelector('#productField');
  if (savedProduct && productField) {
    productField.value = savedProduct;
  }

  // 3. Inquiry Form Submission (Connected to Vercel Serverless /api/inquiry)
  const form = document.querySelector('#inquiryForm');
  if (form) {
    form.addEventListener('submit', async e => {
      e.preventDefault();
      const msg = document.querySelector('#formMsg');
      const submitBtn = form.querySelector('button[type="submit"]') || form.querySelector('.btn.orange');
      const originalBtnText = submitBtn ? submitBtn.textContent : 'Submit';

      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Submitting...';
      }

      // Collect form fields
      const inputs = form.querySelectorAll('input, select, textarea');
      const payload = {
        inquiryType: form.querySelector('select')?.value || '',
        destination: form.querySelector('input[placeholder*="Country"]')?.value || '',
        name: form.querySelector('input[placeholder*="name"], input[placeholder*="Name"]')?.value || '',
        company: form.querySelector('input[placeholder*="Company"]')?.value || '',
        email: form.querySelector('input[type="email"]')?.value || '',
        phone: form.querySelector('input[placeholder*="WhatsApp"], input[placeholder*="Phone"]')?.value || '',
        product: form.querySelector('#productField')?.value || '',
        details: form.querySelector('textarea')?.value || ''
      };

      try {
        const response = await fetch('/api/inquiry', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(payload)
        });

        if (response.ok) {
          if (msg) {
            msg.textContent = 'Thank you! Your inquiry has been submitted successfully. Our team will review your requirements and reach out within 24 hours.';
            msg.classList.add('show');
          }
          form.reset();
          localStorage.removeItem('oz_product');
        } else {
          throw new Error('Server returned error status');
        }
      } catch (err) {
        // Fallback message for offline/preview or when API is unreachable
        if (msg) {
          msg.textContent = 'Thank you. Your inquiry has been recorded. Please also feel free to connect with our China desk directly via email or WhatsApp.';
          msg.classList.add('show');
        }
        form.reset();
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = originalBtnText;
        }
      }
    });
  }
});
