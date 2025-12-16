import type { Schema, Struct } from '@strapi/strapi';

export interface CartCartItem extends Struct.ComponentSchema {
  collectionName: 'components_cart_cart_items';
  info: {
    description: '';
    displayName: 'Cart item';
    icon: 'shopping-basket';
  };
  attributes: {
    product: Schema.Attribute.Relation<'oneToOne', 'api::product.product'>;
    quantity: Schema.Attribute.Decimal &
      Schema.Attribute.Required &
      Schema.Attribute.SetMinMax<
        {
          min: 0;
        },
        number
      >;
  };
}

declare module '@strapi/strapi' {
  export module Public {
    export interface ComponentSchemas {
      'cart.cart-item': CartCartItem;
    }
  }
}
