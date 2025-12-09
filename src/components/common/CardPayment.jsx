import React, { useState } from 'react';

/**
 * Card Payment Component
 * Prepares for future Stripe integration
 */
function CardPayment({ amount, onSuccess, onError, isProcessing, setIsProcessing }) {
  const [cardData, setCardData] = useState({
    cardNumber: '',
    cardName: '',
    expiryDate: '',
    cvv: '',
    saveCard: false
  });

  const [errors, setErrors] = useState({});

  const formatCardNumber = (value) => {
    const v = value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
    const matches = v.match(/\d{4,16}/g);
    const match = (matches && matches[0]) || '';
    const parts = [];

    for (let i = 0; i < match.length; i += 4) {
      parts.push(match.substring(i, i + 4));
    }

    if (parts.length) {
      return parts.join(' ');
    } else {
      return value;
    }
  };

  const formatExpiryDate = (value) => {
    const v = value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
    if (v.length >= 2) {
      return v.slice(0, 2) + '/' + v.slice(2, 4);
    }
    return v;
  };

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    
    let formattedValue = value;
    
    if (name === 'cardNumber') {
      formattedValue = formatCardNumber(value);
    } else if (name === 'expiryDate') {
      formattedValue = formatExpiryDate(value);
    } else if (name === 'cvv') {
      formattedValue = value.replace(/[^0-9]/g, '').slice(0, 3);
    }

    setCardData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : formattedValue
    }));

    // Clear error for this field
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
  };

  const validateForm = () => {
    const newErrors = {};

    // Card number validation (basic)
    const cardNumberDigits = cardData.cardNumber.replace(/\s/g, '');
    if (!cardNumberDigits) {
      newErrors.cardNumber = 'Card number is required';
    } else if (cardNumberDigits.length < 13 || cardNumberDigits.length > 19) {
      newErrors.cardNumber = 'Invalid card number';
    }

    // Cardholder name validation
    if (!cardData.cardName.trim()) {
      newErrors.cardName = 'Cardholder name is required';
    } else if (cardData.cardName.trim().length < 3) {
      newErrors.cardName = 'Name must be at least 3 characters';
    }

    // Expiry date validation
    if (!cardData.expiryDate) {
      newErrors.expiryDate = 'Expiry date is required';
    } else {
      const [month, year] = cardData.expiryDate.split('/');
      const currentYear = new Date().getFullYear() % 100;
      const currentMonth = new Date().getMonth() + 1;
      
      if (!month || !year || month < 1 || month > 12) {
        newErrors.expiryDate = 'Invalid expiry date';
      } else if (parseInt(year) < currentYear || (parseInt(year) === currentYear && parseInt(month) < currentMonth)) {
        newErrors.expiryDate = 'Card has expired';
      }
    }

    // CVV validation
    if (!cardData.cvv) {
      newErrors.cvv = 'CVV is required';
    } else if (cardData.cvv.length < 3) {
      newErrors.cvv = 'Invalid CVV';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const detectCardType = (number) => {
    const patterns = {
      visa: /^4/,
      mastercard: /^5[1-5]/,
      amex: /^3[47]/,
      rupay: /^60|^65|^81|^82/
    };

    for (const [type, pattern] of Object.entries(patterns)) {
      if (pattern.test(number)) {
        return type;
      }
    }
    return 'unknown';
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setIsProcessing(true);

    // Simulate payment processing
    // In production, this will integrate with Stripe
    setTimeout(() => {
      const success = Math.random() > 0.1; // 90% success rate for demo

      if (success) {
        onSuccess({
          transactionId: 'TXN' + Date.now(),
          amount: amount,
          method: 'card',
          cardType: detectCardType(cardData.cardNumber.replace(/\s/g, '')),
          last4: cardData.cardNumber.slice(-4),
          timestamp: new Date().toISOString()
        });
      } else {
        onError({
          message: 'Payment declined. Please try another card.',
          code: 'CARD_DECLINED'
        });
      }

      setIsProcessing(false);
    }, 2000);
  };

  const cardType = detectCardType(cardData.cardNumber.replace(/\s/g, ''));

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Card Number */}
      <div>
        <label className="block text-sm font-semibold text-slate-700 mb-2">
          Card Number
        </label>
        <div className="relative">
          <input
            type="text"
            name="cardNumber"
            value={cardData.cardNumber}
            onChange={handleInputChange}
            placeholder="1234 5678 9012 3456"
            maxLength="19"
            className={`w-full px-4 py-3 rounded-lg border-2 ${
              errors.cardNumber ? 'border-red-500' : 'border-slate-200'
            } focus:border-primary-500 focus:outline-none transition-colors`}
          />
          {cardType !== 'unknown' && (
            <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
              {cardType === 'visa' && <span className="text-blue-600 font-bold text-sm">VISA</span>}
              {cardType === 'mastercard' && <span className="text-red-600 font-bold text-sm">MC</span>}
              {cardType === 'rupay' && <span className="text-green-600 font-bold text-sm">RuPay</span>}
            </div>
          )}
        </div>
        {errors.cardNumber && <p className="mt-1 text-sm text-red-500">{errors.cardNumber}</p>}
      </div>

      {/* Cardholder Name */}
      <div>
        <label className="block text-sm font-semibold text-slate-700 mb-2">
          Cardholder Name
        </label>
        <input
          type="text"
          name="cardName"
          value={cardData.cardName}
          onChange={handleInputChange}
          placeholder="John Doe"
          className={`w-full px-4 py-3 rounded-lg border-2 ${
            errors.cardName ? 'border-red-500' : 'border-slate-200'
          } focus:border-primary-500 focus:outline-none transition-colors uppercase`}
        />
        {errors.cardName && <p className="mt-1 text-sm text-red-500">{errors.cardName}</p>}
      </div>

      {/* Expiry and CVV */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-semibold text-slate-700 mb-2">
            Expiry Date
          </label>
          <input
            type="text"
            name="expiryDate"
            value={cardData.expiryDate}
            onChange={handleInputChange}
            placeholder="MM/YY"
            maxLength="5"
            className={`w-full px-4 py-3 rounded-lg border-2 ${
              errors.expiryDate ? 'border-red-500' : 'border-slate-200'
            } focus:border-primary-500 focus:outline-none transition-colors`}
          />
          {errors.expiryDate && <p className="mt-1 text-sm text-red-500">{errors.expiryDate}</p>}
        </div>

        <div>
          <label className="block text-sm font-semibold text-slate-700 mb-2">
            CVV
          </label>
          <input
            type="text"
            name="cvv"
            value={cardData.cvv}
            onChange={handleInputChange}
            placeholder="123"
            maxLength="3"
            className={`w-full px-4 py-3 rounded-lg border-2 ${
              errors.cvv ? 'border-red-500' : 'border-slate-200'
            } focus:border-primary-500 focus:outline-none transition-colors`}
          />
          {errors.cvv && <p className="mt-1 text-sm text-red-500">{errors.cvv}</p>}
        </div>
      </div>

      {/* Save Card Option */}
      <div className="flex items-center">
        <input
          type="checkbox"
          name="saveCard"
          id="saveCard"
          checked={cardData.saveCard}
          onChange={handleInputChange}
          className="w-4 h-4 text-primary-600 border-slate-300 rounded focus:ring-primary-500"
        />
        <label htmlFor="saveCard" className="ml-2 text-sm text-slate-600">
          Save card for future payments
        </label>
      </div>

      {/* Submit Button */}
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
            <span>Processing Payment...</span>
          </div>
        ) : (
          `Pay ₹${amount}`
        )}
      </button>

      {/* Security Note */}
      <p className="text-xs text-center text-slate-500">
        Your payment information is encrypted and secure
      </p>
    </form>
  );
}

export default CardPayment;
