def migrate(cr, version):
    """Backfill template pricing rows from existing variant subscription prices."""
    cr.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'product_subscription_pricing'
              AND column_name = 'product_tmpl_id'
        )
        """
    )
    if not cr.fetchone()[0]:
        return

    cr.execute(
        """
        UPDATE product_subscription_pricing psp
        SET product_tmpl_id = pp.product_tmpl_id
        FROM product_product pp
        WHERE psp.product_id = pp.id
          AND psp.product_tmpl_id IS NULL
        """
    )

    cr.execute(
        """
        INSERT INTO product_subscription_pricing (
            name, price, period_id, product_tmpl_id, product_id,
            create_uid, write_uid, create_date, write_date
        )
        SELECT DISTINCT ON (pp.product_tmpl_id, psp.period_id)
            psp.name,
            psp.price,
            psp.period_id,
            pp.product_tmpl_id,
            NULL,
            psp.create_uid,
            psp.write_uid,
            NOW() AT TIME ZONE 'UTC',
            NOW() AT TIME ZONE 'UTC'
        FROM product_subscription_pricing psp
        JOIN product_product pp ON pp.id = psp.product_id
        JOIN product_template pt ON pt.id = pp.product_tmpl_id
        WHERE pt.is_recurring = TRUE
          AND psp.product_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM product_subscription_pricing cfg
              WHERE cfg.product_tmpl_id = pp.product_tmpl_id
                AND cfg.product_id IS NULL
                AND cfg.period_id = psp.period_id
          )
        ORDER BY pp.product_tmpl_id, psp.period_id, psp.id
        """
    )
