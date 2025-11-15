IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'unihub')
BEGIN
    CREATE DATABASE unihub;
END
GO

USE unihub;
GO

-- Create users table if not exists
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[users]') AND type in (N'U'))
BEGIN
    CREATE TABLE users (
        id INT IDENTITY(1,1) PRIMARY KEY,
        fullname NVARCHAR(255) NOT NULL,
        email NVARCHAR(255) NOT NULL UNIQUE,
        university NVARCHAR(255) NOT NULL,
        password NVARCHAR(255) NOT NULL,
        created_at DATETIME2 NOT NULL DEFAULT GETDATE()
    );
    
    -- Create index on email for faster lookups
    CREATE INDEX idx_email ON users(email);
END
GO
