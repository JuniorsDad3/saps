@app.route('/assign_case/<int:case_id>', methods=['POST'])
def assign_case(case_id):
    user = User.query.filter(User.AssignedCases < 10).order_by(User.AssignedCases).first()
    if user:
        case = Case.query.get(case_id)
        case.AssignedTo = user.UserID
        case.Status = 'Assigned'

        user.AssignedCases += 1
        db.session.commit()

        return jsonify({"message": f"Case {case.CaseNumber} assigned to {user.Name}"})
    return jsonify({"message": "No available user to assign the case"}), 400
