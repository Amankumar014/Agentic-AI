import React, { useState } from 'react';
import { CardPayment, UpiPayment } from '../components';

/**
 * Payment Page Component
 * Supports Card and UPI payment methods
 */
function Payment() {
  const [paymentMethod, setPaymentMethod] = useState('card'); // 'card' or 'upi'
  const [amount, setAmount] = useState('999');
  const [isProcessing, setIsProcessing] = useState(false);

  const plans = [
    { id: 'basic', name: 'Basic Plan', price: '499', period: 'month', features: ['Live Monitoring', 'Basic Alerts', '7 Days Storage'] },
    { id: 'premium', name: 'Premium Plan', price: '999', period: 'month', features: ['Live Monitoring', 'Advanced AI Alerts', '30 Days Storage', 'Sleep Analytics'] },
    { id: 'pro', name: 'Pro Plan', price: '1999', period: 'month', features: ['Everything in Premium', 'Unlimited Storage', 'Multi-Camera Support', 'Priority Support'] }
  ];

  const [selectedPlan, setSelectedPlan] = useState(plans[1]);

  const handlePaymentSuccess = (paymentDetails) => {
    console.log('Payment successful:', paymentDetails);
    // Here you'll send payment details to your backend
    alert(`Payment successful! Transaction ID: ${paymentDetails.transactionId}`);
  };

  const handlePaymentError = (error) => {
    console.error('Payment failed:', error);
    alert(`Payment failed: ${error.message}`);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-primary-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-slate-800 mb-3">
            Choose Your Plan
          </h1>
          <p className="text-lg text-slate-600">
            Secure payment powered by industry-leading technology
          </p>
        </div>

        {/* Plan Selection */}
        <div className="grid md:grid-cols-3 gap-6 mb-12">
          {plans.map((plan) => (
            <div
              key={plan.id}
              onClick={() => {
                setSelectedPlan(plan);
                setAmount(plan.price);
              }}
              className={`relative cursor-pointer rounded-2xl p-6 transition-all duration-300 ${
                selectedPlan.id === plan.id
                  ? 'bg-gradient-to-br from-primary-500 to-primary-600 text-white shadow-xl scale-105'
                  : 'bg-white text-slate-800 shadow-lg hover:shadow-xl hover:scale-105'
              }`}
            >
              {selectedPlan.id === plan.id && (
                <div className="absolute -top-3 -right-3 bg-green-500 text-white rounded-full p-2">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
              )}
              
              <div className="text-center">
                <h3 className="text-2xl font-bold mb-2">{plan.name}</h3>
                <div className="mb-4">
                  <span className="text-4xl font-bold">₹{plan.price}</span>
                  <span className="text-lg opacity-80">/{plan.period}</span>
                </div>
                <ul className="space-y-2 text-left">
                  {plan.features.map((feature, idx) => (
                    <li key={idx} className="flex items-center space-x-2">
                      <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>

        {/* Payment Section */}
        <div className="grid lg:grid-cols-3 gap-8">
          {/* Payment Method Selection & Form */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-2xl shadow-xl p-8">
              <h2 className="text-2xl font-bold text-slate-800 mb-6">Payment Method</h2>
              
              {/* Payment Method Tabs */}
              <div className="flex space-x-4 mb-8">
                <button
                  onClick={() => setPaymentMethod('card')}
                  className={`flex-1 py-4 px-6 rounded-xl font-semibold transition-all duration-300 ${
                    paymentMethod === 'card'
                      ? 'bg-gradient-to-r from-primary-500 to-primary-600 text-white shadow-lg'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  <div className="flex items-center justify-center space-x-2">
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                    </svg>
                    <span>Card</span>
                  </div>
                </button>
                
                <button
                  onClick={() => setPaymentMethod('upi')}
                  className={`flex-1 py-4 px-6 rounded-xl font-semibold transition-all duration-300 ${
                    paymentMethod === 'upi'
                      ? 'bg-gradient-to-r from-primary-500 to-primary-600 text-white shadow-lg'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  <div className="flex items-center justify-center space-x-2">
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z" />
                    </svg>
                    <span>UPI</span>
                  </div>
                </button>
              </div>

              {/* Payment Forms */}
              {paymentMethod === 'card' ? (
                <CardPayment
                  amount={amount}
                  onSuccess={handlePaymentSuccess}
                  onError={handlePaymentError}
                  isProcessing={isProcessing}
                  setIsProcessing={setIsProcessing}
                />
              ) : (
                <UpiPayment
                  amount={amount}
                  onSuccess={handlePaymentSuccess}
                  onError={handlePaymentError}
                  isProcessing={isProcessing}
                  setIsProcessing={setIsProcessing}
                />
              )}
            </div>
          </div>

          {/* Order Summary */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-2xl shadow-xl p-8 sticky top-8">
              <h3 className="text-xl font-bold text-slate-800 mb-6">Order Summary</h3>
              
              <div className="space-y-4 mb-6">
                <div className="flex justify-between">
                  <span className="text-slate-600">Plan</span>
                  <span className="font-semibold text-slate-800">{selectedPlan.name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-600">Billing Period</span>
                  <span className="font-semibold text-slate-800">Monthly</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-600">Subtotal</span>
                  <span className="font-semibold text-slate-800">₹{selectedPlan.price}</span>
                </div>
                <div className="flex justify-between text-green-600">
                  <span>GST (18%)</span>
                  <span className="font-semibold">₹{(parseFloat(selectedPlan.price) * 0.18).toFixed(2)}</span>
                </div>
              </div>

              <div className="border-t border-slate-200 pt-4 mb-6">
                <div className="flex justify-between items-center">
                  <span className="text-lg font-bold text-slate-800">Total</span>
                  <span className="text-2xl font-bold text-primary-600">
                    ₹{(parseFloat(selectedPlan.price) * 1.18).toFixed(2)}
                  </span>
                </div>
              </div>

              <div className="bg-slate-50 rounded-xl p-4 space-y-2">
                <div className="flex items-center space-x-2 text-sm text-slate-600">
                  <svg className="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                  <span>Secure SSL Encrypted Payment</span>
                </div>
                <div className="flex items-center space-x-2 text-sm text-slate-600">
                  <svg className="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span>100% Safe & Secure</span>
                </div>
                <div className="flex items-center space-x-2 text-sm text-slate-600">
                  <svg className="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
                  </svg>
                  <span>Easy Refund Policy</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Trust Badges */}
        <div className="mt-12 text-center">
          <p className="text-sm text-slate-500 mb-4">Trusted by thousands of parents</p>
          <div className="flex justify-center items-center space-x-8 opacity-60">
            <div className="text-2xl font-bold text-slate-400">VISA</div>
            <div className="text-2xl font-bold text-slate-400">Mastercard</div>
            <div className="text-2xl font-bold text-slate-400">UPI</div>
            <div className="text-2xl font-bold text-slate-400">RuPay</div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Payment;
