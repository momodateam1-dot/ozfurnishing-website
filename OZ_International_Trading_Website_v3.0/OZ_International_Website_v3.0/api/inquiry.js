// Vercel Serverless Function: /api/inquiry
export default async function handler(req, res) {
  // Set CORS headers
  res.setHeader('Access-Control-Allow-Credentials', true);
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS,PATCH,DELETE,POST,PUT');
  res.setHeader(
    'Access-Control-Allow-Headers',
    'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version'
  );

  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const data = typeof req.body === 'string' ? JSON.parse(req.body) : req.body;
    const { inquiryType, destination, name, company, email, phone, product, details } = data || {};

    if (!name || !email) {
      return res.status(400).json({ error: 'Name and Email are required.' });
    }

    console.log('[NEW INQUIRY RECEIVED]:', {
      time: new Date().toISOString(),
      inquiryType,
      destination,
      name,
      company,
      email,
      phone,
      product,
      details
    });

    // Optional: If RESEND_API_KEY is configured in Vercel environment variables,
    // you can send an automatic email notification here.
    if (process.env.RESEND_API_KEY && process.env.NOTIFICATION_EMAIL_TO) {
      await fetch('https://api.resend.com/emails', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${process.env.RESEND_API_KEY}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          from: 'OZ Website <onboarding@resend.dev>',
          to: [process.env.NOTIFICATION_EMAIL_TO],
          subject: `[New Inquiry] ${inquiryType || 'General'} from ${name} (${company || 'Individual'})`,
          text: `
New Inquiry Details:
----------------------------
Inquiry Type: ${inquiryType || 'N/A'}
Destination: ${destination || 'N/A'}
Name: ${name}
Company: ${company || 'N/A'}
Email: ${email}
Phone/WhatsApp: ${phone || 'N/A'}
Product of Interest: ${product || 'N/A'}
Details: ${details || 'N/A'}
----------------------------
Sent from OZ International Website.
          `
        })
      });
    }

    return res.status(200).json({
      success: true,
      message: 'Inquiry received successfully. Our team will contact you shortly.'
    });
  } catch (error) {
    console.error('Inquiry processing error:', error);
    return res.status(500).json({ error: 'Internal server error processing inquiry.' });
  }
}
