-- Create table to store cases
CREATE TABLE Cases (
    CaseID INT IDENTITY(1,1) PRIMARY KEY,
    DateLogged DATETIME DEFAULT GETDATE(),
    TimeLogged TIME DEFAULT CONVERT(TIME, GETDATE()),
    DI_Number NVARCHAR(50),
    Email NVARCHAR(255),
    CellPhone NVARCHAR(15),
    TypeOfCrime NVARCHAR(255),
    CrimeStatus NVARCHAR(50), -- Live/In Progress/Resolved
    CaseDescription NVARCHAR(MAX),
    AssignedTo NVARCHAR(255) NULL,
    Unit NVARCHAR(50) NULL,
    VoiceNote VARBINARY(MAX),
    Image VARBINARY(MAX),
    Status NVARCHAR(50) DEFAULT 'Unassigned'
);

-- Create table to store users (police officers, admins, etc.)
CREATE TABLE Users (
    UserID INT IDENTITY(1,1) PRIMARY KEY,
    FullName NVARCHAR(255),
    Email NVARCHAR(255) UNIQUE,
    PhoneNumber NVARCHAR(15),
    Unit NVARCHAR(50),
    MaxOpenCases INT DEFAULT 10,
    CurrentOpenCases INT DEFAULT 0
);

-- Create table to store submitted documents
CREATE TABLE CertifiedDocuments (
    DocumentID INT IDENTITY(1,1) PRIMARY KEY,
    UserEmail NVARCHAR(255),
    DocumentType NVARCHAR(255),
    SubmittedFile VARBINARY(MAX),
    DigitalSignature VARBINARY(MAX),
    CertificationStatus NVARCHAR(50) DEFAULT 'Pending',
    SubmissionDate DATETIME DEFAULT GETDATE()
);

-- Create table for notifications
CREATE TABLE Notifications (
    NotificationID INT IDENTITY(1,1) PRIMARY KEY,
    CaseID INT FOREIGN KEY REFERENCES Cases(CaseID),
    UserEmail NVARCHAR(255),
    Message NVARCHAR(MAX),
    SentAt DATETIME DEFAULT GETDATE()
);
