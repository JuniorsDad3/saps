SELECT name, type_desc
FROM sys.database_principals
WHERE authentication_type_desc = 'EXTERNAL';

