import React from 'react';

// Renders a customer-safe order summary card containing only approved
// operational fields such as current status, carrier, and delivery estimate.
export default function OrderCard({ orderResult }) {
  if (!orderResult) return null;

  // Handle errors / not found
  if (orderResult.error) {
    return (
      <div className="order-card order-card-error">
        <div className="order-card-header">
          <span className="order-icon">⚠️</span>
          <strong>Order Lookup Notice</strong>
        </div>
        <p className="order-error-message">{orderResult.message || 'Order details unavailable.'}</p>
      </div>
    );
  }

  const order = orderResult.order;
  if (!order) return null;

  const statusClass = `status-pill status-${order.status?.toLowerCase() || 'default'}`;

  return (
    <div className="order-card">
      <div className="order-card-header">
        <div className="order-title">
          <span className="order-icon">📦</span>
          <span className="order-id">{order.order_id}</span>
        </div>
        <span className={statusClass}>
          {order.status ? order.status.toUpperCase() : 'UNKNOWN'}
        </span>
      </div>

      <div className="order-details-grid">
        {order.carrier && (
          <div className="order-detail-item">
            <span className="detail-label">Carrier</span>
            <span className="detail-value">{order.carrier}</span>
          </div>
        )}

        {order.tracking_number && (
          <div className="order-detail-item">
            <span className="detail-label">Tracking</span>
            <span className="detail-value tracking-code">{order.tracking_number}</span>
          </div>
        )}

        {order.estimated_delivery && (
          <div className="order-detail-item">
            <span className="detail-label">Estimated Delivery</span>
            <span className="detail-value">{order.estimated_delivery}</span>
          </div>
        )}

        {order.placed_at && (
          <div className="order-detail-item">
            <span className="detail-label">Placed On</span>
            <span className="detail-value">
              {new Date(order.placed_at).toLocaleDateString(undefined, {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
              })}
            </span>
          </div>
        )}
      </div>

      {order.customer_safe_message && (
        <div className="order-safe-message">
          <span className="info-icon">ℹ️</span>
          <span>{order.customer_safe_message}</span>
        </div>
      )}

      {order.items && order.items.length > 0 && (
        <div className="order-items-section">
          <span className="items-header">Items</span>
          <ul className="order-items-list">
            {order.items.map((item, idx) => (
              <li key={idx} className="order-item-row">
                <span className="item-name">{item.name}</span>
                <span className="item-qty">Qty: {item.quantity}</span>
                {item.final_sale && <span className="item-final-sale">Final Sale</span>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
