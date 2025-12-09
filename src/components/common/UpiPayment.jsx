import React, { useState } from 'react';

// Import UPI app logos
import googlePayLogo from '../../upi_apps_images/googlepay_png.png';
import phonePeLogo from '../../upi_apps_images/phonepe_png.png';
import paytmLogo from '../../upi_apps_images/paytm_png.png';
import amazonPayLogo from '../../upi_apps_images/amazonpay_png.png';
import bhimLogo from '../../upi_apps_images/bhim_png.png';
import mobikwikLogo from '../../upi_apps_images/mobikwik_png.png';

/**
 * UPI Payment Component
 * Supports UPI ID, UPI Apps, and QR Code payment
 */
function UpiPayment({ amount, onSuccess, onError, isProcessing, setIsProcessing }) {
  const [upiMethod, setUpiMethod] = useState('upi-id'); // 'upi-id', 'upi-apps', 'qr-code'
  const [upiId, setUpiId] = useState('');
  const [selectedApp, setSelectedApp] = useState(null);
  const [error, setError] = useState('');

  const upiApps = [
    { id: 'gpay', name: 'Google Pay', logo: googlePayLogo, color: 'from-blue-500 to-blue-600' },
    { id: 'phonepe', name: 'PhonePe', logo: phonePeLogo, color: 'from-purple-500 to-purple-600' },
    { id: 'paytm', name: 'Paytm', logo: paytmLogo, color: 'from-cyan-500 to-cyan-600' },
    { id: 'amazonpay', name: 'Amazon Pay', logo: amazonPayLogo, color: 'from-orange-500 to-orange-600' },
    { id: 'bhim', name: 'BHIM', logo: bhimLogo, color: 'from-red-500 to-red-600' },
    { id: 'mobikwik', name: 'MobiKwik', logo: mobikwikLogo, color: 'from-indigo-500 to-indigo-600' }
  ];

  const validateUpiId = (id) => {
    // UPI ID format: username@bankname
    const upiRegex = /^[\w.-]+@[\w.-]+$/;
    return upiRegex.test(id);
  };

  const handleUpiIdChange = (e) => {
    const value = e.target.value;
    setUpiId(value);
    
    if (error) {
      setError('');
    }
  };

  const handleUpiIdSubmit = async (e) => {
    e.preventDefault();

    if (!upiId.trim()) {
      setError('Please enter your UPI ID');
      return;
    }

    if (!validateUpiId(upiId)) {
      setError('Invalid UPI ID format. Example: yourname@bankname');
      return;
    }

    setIsProcessing(true);

    // Simulate UPI payment verification
    setTimeout(() => {
      const success = Math.random() > 0.1; // 90% success rate for demo

      if (success) {
        onSuccess({
          transactionId: 'UPI' + Date.now(),
          amount: amount,
          method: 'upi-id',
          upiId: upiId,
          timestamp: new Date().toISOString()
        });
      } else {
        onError({
          message: 'UPI payment failed. Please verify your UPI ID and try again.',
          code: 'UPI_FAILED'
        });
      }

      setIsProcessing(false);
    }, 2000);
  };

  const handleAppPayment = (app) => {
    setSelectedApp(app);
    setIsProcessing(true);

    // Simulate UPI app redirect and payment
    setTimeout(() => {
      const success = Math.random() > 0.1; // 90% success rate for demo

      if (success) {
        onSuccess({
          transactionId: 'UPI' + Date.now(),
          amount: amount,
          method: 'upi-app',
          app: app.name,
          timestamp: new Date().toISOString()
        });
      } else {
        onError({
          message: `Payment failed through ${app.name}. Please try again.`,
          code: 'UPI_APP_FAILED'
        });
      }

      setIsProcessing(false);
      setSelectedApp(null);
    }, 2000);
  };

  const generateQRCode = () => {
    // In production, this would generate an actual UPI QR code
    // Format: upi://pay?pa=merchant@bank&pn=MerchantName&am=amount&cu=INR
    return `upi://pay?pa=merchant@bank&pn=LALLA_CARE&am=${amount}&cu=INR&tn=Payment`;
  };

  return (
    <div className="space-y-6">
      {/* UPI Method Selection */}
      <div className="grid grid-cols-3 gap-3">
        <button
          type="button"
          onClick={() => setUpiMethod('upi-id')}
          className={`py-3 px-4 rounded-lg font-semibold text-sm transition-all duration-300 ${
            upiMethod === 'upi-id'
              ? 'bg-gradient-to-r from-primary-500 to-primary-600 text-white shadow-lg'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          UPI ID
        </button>
        <button
          type="button"
          onClick={() => setUpiMethod('upi-apps')}
          className={`py-3 px-4 rounded-lg font-semibold text-sm transition-all duration-300 ${
            upiMethod === 'upi-apps'
              ? 'bg-gradient-to-r from-primary-500 to-primary-600 text-white shadow-lg'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          UPI Apps
        </button>
        <button
          type="button"
          onClick={() => setUpiMethod('qr-code')}
          className={`py-3 px-4 rounded-lg font-semibold text-sm transition-all duration-300 ${
            upiMethod === 'qr-code'
              ? 'bg-gradient-to-r from-primary-500 to-primary-600 text-white shadow-lg'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          QR Code
        </button>
      </div>

      {/* UPI ID Input */}
      {upiMethod === 'upi-id' && (
        <form onSubmit={handleUpiIdSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              Enter UPI ID
            </label>
            <input
              type="text"
              value={upiId}
              onChange={handleUpiIdChange}
              placeholder="yourname@paytm"
              className={`w-full px-4 py-3 rounded-lg border-2 ${
                error ? 'border-red-500' : 'border-slate-200'
              } focus:border-primary-500 focus:outline-none transition-colors`}
              disabled={isProcessing}
            />
            {error && <p className="mt-1 text-sm text-red-500">{error}</p>}
            <p className="mt-2 text-xs text-slate-500">
              Example: 9876543210@paytm, yourname@ybl, user@okhdfcbank
            </p>
          </div>

          <button
            type="submit"
            disabled={isProcessing}
            className={`w-full py-4 rounded-lg font-bold text-white transition-all duration-300 ${
              isProcessing
                ? 'bg-slate-400 cursor-not-allowed'
                : 'bg-gradient-to-r from-primary-500 to-primary-600 hover:from-primary-600 hover:to-primary-700 shadow-lg hover:shadow-xl'
            }`}
          >
            {isProcessing ? (
              <div className="flex items-center justify-center space-x-2">
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                <span>Verifying UPI ID...</span>
              </div>
            ) : (
              `Pay ₹${amount} via UPI`
            )}
          </button>
        </form>
      )}

      {/* UPI Apps Selection */}
      {upiMethod === 'upi-apps' && (
        <div className="space-y-4">
          <p className="text-sm font-semibold text-slate-700">
            Choose your preferred UPI app
          </p>
          <div className="grid grid-cols-2 gap-4">
            {upiApps.map((app) => (
              <button
                key={app.id}
                type="button"
                onClick={() => handleAppPayment(app)}
                disabled={isProcessing}
                className={`relative p-4 rounded-xl border-2 transition-all duration-300 ${
                  selectedApp?.id === app.id
                    ? 'border-primary-500 bg-primary-50'
                    : 'border-slate-200 hover:border-slate-300 hover:shadow-md'
                } ${isProcessing ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
              >
                <div className="flex items-center space-x-3">
                  <div className="w-14 h-14 rounded-xl bg-white shadow-md flex items-center justify-center p-2 flex-shrink-0">
                    <img 
                      src={app.logo} 
                      alt={app.name} 
                      className="w-full h-full object-contain"
                    />
                  </div>
                  <div className="text-left flex-1">
                    <p className="font-bold text-slate-800">{app.name}</p>
                    <p className="text-xs text-slate-500">Pay via app</p>
                  </div>
                </div>
                {selectedApp?.id === app.id && isProcessing && (
                  <div className="absolute inset-0 bg-white/80 rounded-xl flex items-center justify-center">
                    <div className="w-6 h-6 border-2 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
                  </div>
                )}
              </button>
            ))}
          </div>
          <p className="text-xs text-center text-slate-500">
            You'll be redirected to your selected app to complete the payment
          </p>
        </div>
      )}

      {/* QR Code */}
      {upiMethod === 'qr-code' && (
        <div className="space-y-4">
          <div className="bg-gradient-to-br from-slate-50 to-slate-100 rounded-xl p-8">
            <div className="text-center space-y-4">
              <p className="text-sm font-semibold text-slate-700">
                Scan QR Code to Pay
              </p>
              
              {/* QR Code Placeholder */}
              <div className="inline-block bg-white p-6 rounded-2xl shadow-xl">
                <div className="w-48 h-48 bg-white border-4 border-slate-200 rounded-lg flex items-center justify-center">
                  <div className="text-center">
                    <svg className="w-32 h-32 mx-auto text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h.01M5 8h2a1 1 0 001-1V5a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1zm12 0h2a1 1 0 001-1V5a1 1 0 00-1-1h-2a1 1 0 00-1 1v2a1 1 0 001 1zM5 20h2a1 1 0 001-1v-2a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1z" />
                    </svg>
                    <p className="text-xs text-slate-500 mt-2">QR Code</p>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <p className="text-2xl font-bold text-primary-600">₹{amount}</p>
                <p className="text-sm text-slate-600">
                  Open any UPI app and scan this QR code
                </p>
              </div>

              {/* Supported Apps */}
              <div className="pt-4 border-t border-slate-200">
                <p className="text-xs text-slate-500 mb-3">Scan with any UPI app</p>
                <div className="flex justify-center space-x-3">
                  {upiApps.slice(0, 4).map((app) => (
                    <div
                      key={app.id}
                      className="w-12 h-12 rounded-lg bg-white shadow-md flex items-center justify-center p-2 transform hover:scale-110 transition-transform"
                    >
                      <img 
                        src={app.logo} 
                        alt={app.name} 
                        className="w-full h-full object-contain"
                      />
                    </div>
                  ))}
                </div>
              </div>

              {/* Manual Verification */}
              <button
                type="button"
                onClick={() => {
                  setIsProcessing(true);
                  // Simulate payment verification
                  setTimeout(() => {
                    onSuccess({
                      transactionId: 'UPI' + Date.now(),
                      amount: amount,
                      method: 'qr-code',
                      timestamp: new Date().toISOString()
                    });
                    setIsProcessing(false);
                  }, 2000);
                }}
                disabled={isProcessing}
                className={`mt-4 px-6 py-3 rounded-lg font-semibold text-sm transition-all duration-300 ${
                  isProcessing
                    ? 'bg-slate-400 text-white cursor-not-allowed'
                    : 'bg-green-500 text-white hover:bg-green-600 shadow-lg hover:shadow-xl'
                }`}
              >
                {isProcessing ? (
                  <div className="flex items-center space-x-2">
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    <span>Verifying Payment...</span>
                  </div>
                ) : (
                  'I have completed the payment'
                )}
              </button>
            </div>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-start space-x-3">
              <svg className="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div className="text-sm text-blue-800">
                <p className="font-semibold mb-1">How to pay via QR Code:</p>
                <ol className="list-decimal list-inside space-y-1 text-xs">
                  <li>Open any UPI app (GPay, PhonePe, Paytm, etc.)</li>
                  <li>Tap on "Scan QR Code" option</li>
                  <li>Scan the QR code displayed above</li>
                  <li>Verify the amount and complete the payment</li>
                  <li>Click "I have completed the payment" button</li>
                </ol>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Security Note */}
      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
        <div className="flex items-center space-x-2">
          <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
          <p className="text-sm text-green-800">
            <span className="font-semibold">100% Safe & Secure.</span> All UPI transactions are protected by NPCI
          </p>
        </div>
      </div>
    </div>
  );
}

export default UpiPayment;
