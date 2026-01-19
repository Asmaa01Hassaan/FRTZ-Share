def migrate(cr, version):
    """
    Rename column 'divisions' to 'division_id' in res_partner table
    This fixes the database schema mismatch where the database has 'divisions'
    but the code expects 'division_id'
    """
    cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='res_partner' 
        AND column_name='divisions'
    """)
    
    if cr.fetchone():
        # Column exists, rename it
        cr.execute("ALTER TABLE res_partner RENAME COLUMN divisions TO division_id")
        cr.execute("COMMENT ON COLUMN res_partner.division_id IS 'Department (Many2one to contact.division)'")





